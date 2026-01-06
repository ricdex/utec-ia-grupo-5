"""
Financial calculation utilities
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
import math


@dataclass
class ProductAllocation:
    product_id: str
    product_name: str
    percentage: float
    amount: float
    annual_rate: float


@dataclass
class PortfolioMetrics:
    expected_return: float
    expected_volatility: float
    expected_liquidity: str
    sharpe_ratio: float


class FinanceCalculator:
    """Financial calculation utilities"""

    @staticmethod
    def calculate_compound_return(
        initial_amount: float,
        annual_rate: float,
        years: float,
        monthly_contributions: float = 0
    ) -> float:
        """Calculate compound return with optional monthly contributions"""
        months = int(years * 12)
        rate_per_month = annual_rate / 12

        # With monthly contributions
        if monthly_contributions > 0:
            fv = initial_amount * (1 + rate_per_month) ** months
            fv += monthly_contributions * (((1 + rate_per_month) ** months - 1) / rate_per_month)
        else:
            fv = initial_amount * (1 + rate_per_month) ** months

        return fv

    @staticmethod
    def calculate_portfolio_metrics(
        allocations: List[ProductAllocation],
        risk_free_rate: float = 0.045
    ) -> PortfolioMetrics:
        """
        Calculate portfolio expected return, volatility, and liquidity
        """
        expected_return = sum(
            (alloc.percentage / 100) * alloc.annual_rate
            for alloc in allocations
        )

        # Volatility estimation based on product types
        volatility_map = {
            0: 0.05,   # conservador
            1: 0.12,   # moderado
            2: 0.20    # agresivo
        }

        # Simple volatility calculation (in production, use covariance matrix)
        weighted_volatility = 0.0
        for alloc in allocations:
            # Estimate risk level from annual_rate
            if alloc.annual_rate <= 0.050:
                risk_level = 0
            elif alloc.annual_rate <= 0.085:
                risk_level = 1
            else:
                risk_level = 2

            weighted_volatility += (alloc.percentage / 100) * volatility_map[risk_level]

        # Liquidity assessment
        liquidity_score = 0
        for alloc in allocations:
            # In real implementation, fetch liquidity from product
            liquidity_score += (alloc.percentage / 100) * 0.7  # Assumes media liquidity

        liquidity = "media"
        if liquidity_score > 0.8:
            liquidity = "alta"
        elif liquidity_score < 0.5:
            liquidity = "baja"

        # Sharpe ratio
        sharpe = (expected_return - risk_free_rate) / weighted_volatility if weighted_volatility > 0 else 0

        return PortfolioMetrics(
            expected_return=expected_return,
            expected_volatility=weighted_volatility,
            expected_liquidity=liquidity,
            sharpe_ratio=sharpe
        )

    @staticmethod
    def calculate_final_amount(
        initial_amount: float,
        annual_rate: float,
        months: int
    ) -> float:
        """Calculate final amount after investment period"""
        years = months / 12
        rate_per_month = annual_rate / 12
        fv = initial_amount * ((1 + rate_per_month) ** months)
        return fv

    @staticmethod
    def estimate_withdrawal_penalty(
        amount: float,
        withdrawal_time_months: int,
        withdrawal_window_months: int,
        penalty_pct: float
    ) -> Tuple[float, bool]:
        """
        Estimate withdrawal penalty if withdrawn early
        Returns (net_amount, has_penalty)
        """
        if withdrawal_time_months > withdrawal_window_months:
            return (amount, False)

        penalty_amount = amount * (penalty_pct / 100)
        net_amount = amount - penalty_amount
        return (net_amount, True)

    @staticmethod
    def diversify_portfolio(
        total_amount: float,
        eligible_products: List[Dict],
        client_risk_profile: str
    ) -> List[ProductAllocation]:
        """
        Create diversified portfolio allocation based on risk profile
        Allocations are aligned with guardrails and hardcoded per profile
        Returns list of ProductAllocation objects
        """

        # Define allocation percentages by risk profile
        # Aligned with guardrails: conservador gets 0% aggressive
        profile_allocations = {
            "conservador": {
                "conservador": 70,
                "moderado": 30,
                "agresivo": 0  # Conservative profiles: NO aggressive products
            },
            "moderado": {
                "conservador": 30,
                "moderado": 50,
                "agresivo": 20
            },
            "agresivo": {
                "conservador": 10,
                "moderado": 30,
                "agresivo": 60
            }
        }

        profile_pcts = profile_allocations.get(client_risk_profile, profile_allocations["moderado"])

        # Group products by type
        products_by_type = {}
        for product in eligible_products:
            ptype = product['type']
            if ptype not in products_by_type:
                products_by_type[ptype] = []
            products_by_type[ptype].append(product)

        # Select best product from each type
        allocations = []
        for ptype, pct in profile_pcts.items():
            if ptype in products_by_type and pct > 0:
                # Select product with best rate
                best_product = max(
                    products_by_type[ptype],
                    key=lambda p: p['annual_rate']
                )

                allocation_amount = total_amount * (pct / 100)

                allocations.append(ProductAllocation(
                    product_id=best_product['id'],
                    product_name=best_product['name'],
                    percentage=pct,
                    amount=allocation_amount,
                    annual_rate=best_product['annual_rate']
                ))

        return allocations

    @staticmethod
    def validate_portfolio_constraints(
        allocations: List[ProductAllocation],
        client_profile: Dict,
        market_context: Dict
    ) -> Tuple[bool, List[str]]:
        """
        Validate portfolio against client constraints
        Returns (is_valid, list_of_violations)
        """
        violations = []

        # Check allocation limits by risk profile
        # Note: This is a simplified check. Full validation happens in guardrails.py
        risk_profile = client_profile.get('risk_profile', 'moderado')

        # Basic sanity check: conservative profile should not have aggressive products
        if risk_profile == 'conservador':
            aggressive_pct = sum(
                a.percentage for a in allocations
                if a.annual_rate > 0.085  # Approximate aggressive threshold
            )
            if aggressive_pct > 0:
                violations.append(
                    f"Conservative profile should not have aggressive products ({aggressive_pct:.1f}%)"
                )

        # Check target return is achievable
        portfolio_return = sum(
            (a.percentage / 100) * a.annual_rate
            for a in allocations
        )

        target_return = client_profile.get('target_return_pct', 0)
        if portfolio_return < target_return:
            violations.append(
                f"Portfolio return {portfolio_return:.2%} below target {target_return:.2%}"
            )

        # Check minimum amounts
        for alloc in allocations:
            if alloc.amount < 1000:  # Minimum investment
                violations.append(
                    f"Allocation to {alloc.product_name} (${alloc.amount:.0f}) below minimum $1000"
                )

        return (len(violations) == 0, violations)


class SimulationEngine:
    """Portfolio simulation and scenario analysis"""

    @staticmethod
    def simulate_portfolio(
        allocations: List[ProductAllocation],
        months: int,
        scenarios: List[str] = ["base", "optimistic", "pessimistic"]
    ) -> Dict:
        """
        Simulate portfolio performance under different scenarios
        """
        results = {}

        for scenario in scenarios:
            scenario_multiplier = {
                "pessimistic": 0.7,
                "base": 1.0,
                "optimistic": 1.3
            }.get(scenario, 1.0)

            final_values = []
            for alloc in allocations:
                adjusted_rate = alloc.annual_rate * scenario_multiplier
                final = FinanceCalculator.calculate_final_amount(
                    alloc.amount,
                    adjusted_rate,
                    months
                )
                final_values.append(final)

            total_final = sum(final_values)
            total_return = ((total_final - sum(a.amount for a in allocations)) /
                           sum(a.amount for a in allocations))

            results[scenario] = {
                "final_value": total_final,
                "total_return": total_return,
                "allocation_values": final_values
            }

        return results
