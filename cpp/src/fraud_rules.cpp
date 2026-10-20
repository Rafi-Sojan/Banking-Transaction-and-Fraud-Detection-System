#include "fraud_rules.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <utility>

namespace banking::fraud {
namespace {

std::string normalized(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char character) {
        return static_cast<char>(std::tolower(character));
    });
    return value;
}

bool containsCategory(const std::vector<std::string>& categories, const std::string& category) {
    const auto target = normalized(category);
    return std::any_of(categories.begin(), categories.end(), [&target](const std::string& candidate) {
        return normalized(candidate) == target;
    });
}

}  // namespace

FraudRules::FraudRules(RuleConfig config) : config_(std::move(config)) {}

double clampRiskScore(double score) {
    return std::max(0.0, std::min(score, 1.0));
}

std::string riskLevelForScore(double score) {
    const auto normalizedScore = clampRiskScore(score);
    if (normalizedScore >= 0.85) {
        return "critical";
    }
    if (normalizedScore >= 0.60) {
        return "high";
    }
    if (normalizedScore >= 0.30) {
        return "medium";
    }
    return "low";
}

FraudEvaluation FraudRules::evaluate(const TransactionFeatures& transaction) const {
    FraudEvaluation evaluation;
    double score = 0.0;

    const auto addRule = [&evaluation, &score](
        const std::string& ruleId,
        bool triggered,
        double contribution,
        const std::string& reason
    ) {
        const auto appliedContribution = triggered ? clampRiskScore(contribution) : 0.0;
        evaluation.rules.push_back({ruleId, triggered, appliedContribution, triggered ? reason : ""});
        if (triggered) {
            score += appliedContribution;
            evaluation.reasons.push_back(reason);
        }
    };

    addRule(
        "large_amount",
        transaction.amount >= config_.large_amount_threshold,
        config_.large_amount_contribution,
        "Transaction amount meets or exceeds the configured large-amount threshold"
    );

    addRule(
        "rapid_frequency",
        transaction.transaction_count_10m >= config_.rapid_frequency_threshold,
        config_.rapid_frequency_contribution,
        "Transaction frequency exceeds the configured short-window threshold"
    );

    addRule(
        "repeated_failed_attempts",
        transaction.failed_attempts_1h >= config_.failed_attempts_threshold,
        config_.failed_attempts_contribution,
        "Repeated failed attempts were observed in the configured time window"
    );

    addRule(
        "new_device",
        transaction.is_new_device,
        config_.new_device_contribution,
        "Transaction originated from a device not previously associated with the account"
    );

    addRule(
        "new_location",
        transaction.is_new_location,
        config_.new_location_contribution,
        "Transaction originated from a location not previously associated with the account"
    );

    const bool crossBorder = !transaction.country.empty()
        && !transaction.home_country.empty()
        && normalized(transaction.country) != normalized(transaction.home_country);
    addRule(
        "cross_border",
        crossBorder,
        config_.cross_border_contribution,
        "Transaction country differs from the account's home country"
    );

    const bool youngAccount = transaction.account_age_days >= 0
        && transaction.account_age_days < config_.minimum_account_age_days;
    addRule(
        "new_account",
        youngAccount,
        0.10,
        "Transaction originated from an account newer than the configured minimum age"
    );

    addRule(
        "high_risk_merchant",
        containsCategory(config_.high_risk_merchant_categories, transaction.merchant_category),
        config_.high_risk_merchant_contribution,
        "Merchant category is configured as high risk"
    );

    evaluation.rule_score = clampRiskScore(score);
    evaluation.risk_level = riskLevelForScore(evaluation.rule_score);
    return evaluation;
}

}  // namespace banking::fraud
