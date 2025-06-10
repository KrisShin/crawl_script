from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Optional

from app.xueqiu.model import XueqiuRebalancing, XueqiuZHIndex


async def calculate_portfolio_stock_contributions(
    min_abs_contribution_pct: Optional[float] = None, pnl_filter: Optional[str] = None  # 'positive', 'negative', or None
) -> Dict[str, Any]:
    """
    计算雪球组合中每只股票的交易历史和盈利贡献。

    Args:
        min_abs_contribution_pct: 过滤掉贡献度绝对值小于此值的股票。
        pnl_filter: 'positive' 只看盈利的股票, 'negative' 只看亏损的股票。

    Returns:
        一个字典，key为组合代码，value为该组合的详细分析结果。
    """
    last_id = 0

    zh_indices = await XueqiuZHIndex.filter(id__gt=last_id).order_by('id').limit(100)
    rebalancing_data = await XueqiuRebalancing.filter(symbol__in=[zh.symbol for zh in zh_indices]).order_by('symbol', 'id')
    while zh_indices:
        # 按组合代码组织调仓数据，并按时间排序
        portfolio_histories = defaultdict(list)
        for reb in rebalancing_data:
            portfolio_histories[reb.symbol].append(reb)

        # 组织组合的元数据
        indices_map = {index.symbol: index for index in zh_indices}

        final_results = {}

        # 遍历每一个有历史记录的组合
        for symbol, history in portfolio_histories.items():
            if symbol not in indices_map:
                continue

            index_info = indices_map[symbol]

            # 计算组合初始价值
            # 避免除以零或负数的情况
            if (1 + index_info.total_gain) <= 0:
                initial_portfolio_value = 0
            else:
                initial_portfolio_value = index_info.net_value / (1 + index_info.total_gain) / 100

            stock_tracker = {}  # 用于追踪组合内每只股票的状态

            # 1. 遍历时间线，计算已实现盈亏和更新持仓
            for record in history:
                for trade in record.rebalancing_histories:
                    stock_symbol = trade["stock_symbol"]

                    # 初始化股票追踪器
                    if stock_symbol not in stock_tracker:
                        stock_tracker[stock_symbol] = {
                            "stock_name": trade["stock_name"],
                            "transactions": [],
                            "current_shares": 0,
                            "average_cost_basis": 0.0,
                            "realized_pnl": 0.0,
                        }

                    tracker = stock_tracker[stock_symbol]

                    # 记录交易
                    tracker["transactions"].append(
                        {
                            "date": datetime.fromtimestamp(record.created_at).strftime('%Y-%m-%d'),
                            "action": trade["action"],
                            "price": trade["price"],
                            "volume": trade["volume"],
                            "amount": trade["price"] * trade["volume"],
                        }
                    )

                    # 更新持仓成本和已实现盈亏
                    if trade["action"] == "buy":
                        total_cost = (tracker["average_cost_basis"] * tracker["current_shares"]) + (trade["price"] * trade["volume"])
                        tracker["current_shares"] += trade["volume"]
                        tracker["average_cost_basis"] = total_cost / tracker["current_shares"] if tracker["current_shares"] > 0 else 0

                    elif trade["action"] == "sell":
                        sale_pnl = (trade["price"] - tracker["average_cost_basis"]) * trade["volume"]
                        tracker["realized_pnl"] += sale_pnl
                        tracker["current_shares"] -= trade["volume"]
                        if tracker["current_shares"] == 0:
                            tracker["average_cost_basis"] = 0  # 清仓后成本归零

            # 2. 计算未实现盈亏和总贡献
            final_stock_performance = []

            # 获取最新持仓快照以确定最新价格
            latest_holdings = {}
            if history:  # 确保历史记录不为空
                latest_holdings = {h['stock_symbol']: h['price'] for h in history[-1].holdings}

            for symbol, tracker in stock_tracker.items():
                unrealized_pnl = 0.0
                if tracker["current_shares"] > 0 and symbol in latest_holdings:
                    latest_price = latest_holdings[symbol]
                    unrealized_pnl = (latest_price - tracker["average_cost_basis"]) * tracker["current_shares"]

                total_pnl = tracker["realized_pnl"] + unrealized_pnl

                contribution_pct = 0.0
                if initial_portfolio_value > 0:
                    contribution_pct = (total_pnl / initial_portfolio_value) * 100

                performance_data = {
                    "stock_symbol": symbol,  # 股票代码
                    "stock_name": tracker["stock_name"],  # 股票名称
                    "total_pnl": round(total_pnl, 2),  # 该股票已经实现的盈亏总额
                    "contribution_pct": round(contribution_pct, 2),  # 该股票贡献百分比
                    "transactions": tracker["transactions"],  # 交易
                }

                # --- 在此处应用过滤器 ---

                # 1. 根据 PNL 过滤
                if pnl_filter:
                    if pnl_filter == 'positive' and performance_data['total_pnl'] <= 0:
                        continue
                    if pnl_filter == 'negative' and performance_data['total_pnl'] >= 0:
                        continue

                # 2. 根据贡献度过滤
                if min_abs_contribution_pct is not None:
                    if abs(performance_data['contribution_pct']) < min_abs_contribution_pct:
                        continue

                final_stock_performance.append(performance_data)

            final_results[index_info.symbol] = {
                "portfolio_name": index_info.name,  # 组合名称
                "owner_name": index_info.owner_name,  # 组合创建者名字
                "initial_portfolio_value": round(initial_portfolio_value, 2),  # 初始价值
                "current_net_value": index_info.net_value,  # 当前净值
                "total_gain_pct": round(index_info.total_gain * 100, 2),  # 总收益
                "stocks_performance": final_stock_performance,  # 所有股票表现
            }
        last_id = zh_indices[-1].id
        zh_indices = await XueqiuZHIndex.filter(id__gt=last_id).order_by('id').limit(100)
        rebalancing_data = await XueqiuRebalancing.filter(symbol__in=[zh.symbol for zh in zh_indices]).order_by('symbol', 'id')
    return final_results
