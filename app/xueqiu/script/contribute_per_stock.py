import ast
from collections import defaultdict
from datetime import datetime
import json
from typing import Any, Dict, List, Optional, Tuple

# 假设这些是您的 ORM 模型
from app.xueqiu.model import XueqiuRebalancing, XueqiuRebalancingNew, XueqiuZHIndex, XueqiuZHStockContrib


# --- 核心算法实现 ---

BATCH_SIZE = 200


def extract_transaction_details(trade: dict) -> Tuple[str, Optional[float], Optional[float]]:
    """
    从单条调仓历史记录中提取真实的交易活动详情。

    Args:
        trade: 一条 rebalancing_histories 中的字典。

    Returns:
        一个元组 (action, transaction_price, transaction_volume)。
        action: 'buy', 'sell', 'no_change', 'invalid_trade'.
        transaction_price: 本次交易的价格。
        transaction_volume: 本次交易的数量。
    """
    current_volume = trade.get('volume') or 0
    prev_volume = trade.get('prev_volume') or 0

    volume_diff = current_volume - prev_volume

    if volume_diff > 1e-9:
        action = 'buy'
        transaction_price = trade.get('price')
        transaction_volume = volume_diff
    elif volume_diff < -1e-9:
        action = 'sell'
        transaction_price = trade.get('prev_price')
        transaction_volume = -volume_diff  # 交易量为正数
    else:
        return 'no_change', None, 0

    # 如果有仓位变动，但价格或交易量信息不合法，则视为无效交易
    if transaction_price is None or transaction_volume <= 0:
        return 'invalid_trade', None, 0

    return action, transaction_price, transaction_volume


async def calculate_portfolio_stock_contributions(
    min_abs_contribution_pct: Optional[float] = None, pnl_filter: Optional[str] = None  # 'positive', 'negative', or None
) -> None:
    """
    计算雪球组合中每只股票的交易历史和盈利贡献。

    Args:
        min_abs_contribution_pct: 过滤掉贡献度绝对值小于此值的股票。
        pnl_filter: 'positive' 只看盈利的股票, 'negative' 只看亏损的股票。
    """
    last_id = 0  # 从头开始

    while True:
        zh_indices = await XueqiuZHIndex.filter(id__gt=last_id).order_by('id').limit(BATCH_SIZE)
        if not zh_indices:
            print("所有组合计算完毕。")
            break

        indices_map = {index.symbol: index for index in zh_indices}
        symbols_list = list(indices_map.keys())

        rebalancing_data_old = await XueqiuRebalancing.filter(symbol__in=symbols_list)
        rebalancing_data_new = await XueqiuRebalancingNew.filter(symbol__in=symbols_list)

        rebalancing_data = sorted(rebalancing_data_old + rebalancing_data_new, key=lambda r: (r.symbol, r.created_at))

        portfolio_histories = defaultdict(list)
        for reb in rebalancing_data:
            # 安全地将 string 转换为 list of dicts
            try:
                # 优先尝试标准JSON解析
                reb.holdings = json.loads(reb.holdings or "[]")
                reb.rebalancing_histories = json.loads(reb.rebalancing_histories or "[]")
            except (json.JSONDecodeError, TypeError):
                try:
                    # 如果JSON解析失败，尝试作为Python字面量解析
                    reb.holdings = ast.literal_eval(reb.holdings or "[]")
                    reb.rebalancing_histories = ast.literal_eval(reb.rebalancing_histories or "[]")
                except (ValueError, SyntaxError) as e:
                    print(f"警告: 无法解析组合 {reb.symbol} 的数据 (记录ID: {reb.id})。数据可能已损坏。错误: {e}")
                    continue  # 跳过这条损坏的记录
            portfolio_histories[reb.symbol].append(reb)

        # 检查在索引中但无任何历史记录的组合
        symbols_with_history = set(portfolio_histories.keys())
        for symbol, index_info in indices_map.items():
            if symbol not in symbols_with_history:
                print(f"--- 计算失败: {index_info.name}({symbol}) ---")
                print(f"  原因: 在调仓记录表中找不到该组合的任何历史数据。")
                print("-" * (23 + len(f"{index_info.name}({symbol})")))

        for symbol, history in portfolio_histories.items():
            if symbol not in indices_map:
                continue

            index_info = indices_map[symbol]

            # 检查1: 初始投资额是否有效
            if index_info.total_gain <= -100:
                print(f"--- 计算失败: {index_info.name}({symbol}) ---")
                print(f"  原因: 总收益率为 {index_info.total_gain}%, 无法计算有效的初始投资额。")
                print("-" * (23 + len(f"{index_info.name}({symbol})")))
                continue

            initial_portfolio_value = index_info.net_value / (1 + index_info.total_gain / 100.0)
            if initial_portfolio_value <= 0:
                print(f"--- 计算失败: {index_info.name}({symbol}) ---")
                print(
                    f"  原因: 计算出的初始投资额为 {initial_portfolio_value:.2f}, 无法作为有效基准。(净值: {index_info.net_value}, 总收益率: {index_info.total_gain}%)"
                )
                print("-" * (23 + len(f"{index_info.name}({symbol})")))
                continue

            stock_tracker = defaultdict(
                lambda: {
                    "stock_name": "",
                    "transactions": [],
                    "current_shares": 0.0,
                    "average_cost_basis": 0.0,
                    "realized_pnl": 0.0,
                }
            )

            # 增强的诊断计数器
            diag_total_histories = 0
            diag_potential_trades = 0
            diag_invalid_trades = 0
            has_valid_trades = False

            for record in history:
                for trade in record.rebalancing_histories:
                    diag_total_histories += 1
                    stock_symbol = trade.get("stock_symbol")
                    if not stock_symbol:
                        continue

                    action, transaction_price, transaction_volume = extract_transaction_details(trade)

                    if action in ['buy', 'sell']:
                        has_valid_trades = True
                        diag_potential_trades += 1

                        tracker = stock_tracker[stock_symbol]
                        if not tracker["stock_name"]:
                            tracker["stock_name"] = trade.get("stock_name", "N/A")

                        tracker["transactions"].append(
                            {
                                "date": datetime.fromtimestamp(record.created_at / 1000).strftime('%Y-%m-%d'),
                                "action": action,
                                "price": transaction_price,
                                "volume": transaction_volume,
                                "amount": transaction_price * transaction_volume,
                            }
                        )

                        if action == "buy":
                            total_cost = (tracker["average_cost_basis"] * tracker["current_shares"]) + (
                                transaction_price * transaction_volume
                            )
                            tracker["current_shares"] += transaction_volume
                            if tracker["current_shares"] > 1e-9:
                                tracker["average_cost_basis"] = total_cost / tracker["current_shares"]
                        elif action == "sell":
                            if tracker["average_cost_basis"] > 0:
                                tracker["realized_pnl"] += (transaction_price - tracker["average_cost_basis"]) * transaction_volume
                            tracker["current_shares"] -= transaction_volume
                            if tracker["current_shares"] < 1e-9:
                                tracker["current_shares"] = 0
                                tracker["average_cost_basis"] = 0
                    elif action == 'invalid_trade':
                        diag_potential_trades += 1
                        diag_invalid_trades += 1

            if not has_valid_trades:
                print(f"--- 计算失败: {index_info.name}({symbol}) ---")
                if diag_potential_trades > 0:
                    print(
                        f"  原因: 在 {diag_total_histories} 条记录中发现 {diag_potential_trades} 次潜在交易, 但全部因数据不完整(如缺少价格)而无法计算。"
                    )
                else:
                    print(f"  原因: 在 {diag_total_histories} 条历史记录中未发现任何仓位变化。")
                print("-" * (23 + len(f"{index_info.name}({symbol})")))
                continue

            final_stock_performance = []
            latest_holdings = {h['stock_symbol']: h['price'] for h in history[-1].holdings if h.get('stock_symbol')} if history else {}

            for stock_symbol, tracker in stock_tracker.items():
                unrealized_pnl = 0.0
                if tracker["current_shares"] > 1e-9 and stock_symbol in latest_holdings:
                    latest_price = latest_holdings[stock_symbol]
                    if latest_price is not None and tracker["average_cost_basis"] > 0:
                        unrealized_pnl = (latest_price - tracker["average_cost_basis"]) * tracker["current_shares"]

                total_pnl = tracker["realized_pnl"] + unrealized_pnl
                contribution_pct = (total_pnl / initial_portfolio_value) * 100 if initial_portfolio_value > 0 else 0

                performance_data = {
                    "stock_symbol": stock_symbol,
                    "stock_name": tracker["stock_name"],
                    "total_pnl": round(total_pnl, 2),
                    "contribution_pct": round(contribution_pct, 2),
                    "transactions": tracker["transactions"],
                }

                if pnl_filter and ((pnl_filter == 'positive' and total_pnl <= 0) or (pnl_filter == 'negative' and total_pnl >= 0)):
                    continue
                if min_abs_contribution_pct is not None and abs(contribution_pct) < min_abs_contribution_pct:
                    continue
                final_stock_performance.append(performance_data)

            if not final_stock_performance:
                print(f"--- 计算完成(无结果): {index_info.name}({symbol}) ---")
                if stock_tracker:
                    print(f"  原因: 追踪到 {len(stock_tracker)} 只股票的交易, 但没有股票满足最终的输出条件(如盈利过滤、贡献度过滤)。")
                print("-" * (30 + len(f"{index_info.name}({symbol})")))
            else:
                print(f"--- 计算成功: {index_info.name}({symbol}) | 发现 {len(final_stock_performance)} 只符合条件的股票 ---")

            await XueqiuZHStockContrib.create(
                symbol=index_info.symbol,
                portfolio_name=index_info.name,
                owner_name=index_info.owner_name,
                initial_portfolio_value=round(initial_portfolio_value, 2),
                current_net_value=index_info.net_value,
                total_gain_pct=round(index_info.total_gain, 2),
                stocks_performance=final_stock_performance,
            )

        last_id = zh_indices[-1].id
