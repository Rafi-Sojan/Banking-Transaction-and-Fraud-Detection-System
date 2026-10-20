#pragma once

#include <string>
#include <vector>

namespace banking::fraud {

struct TransactionFeatures {
    std::string transaction_id;
    double amount{0.0};
    std::string transaction_type;
    std::string merchant_category;
    std::string country;
    std::string home_country;
    int transaction_count_10m{0};
    int failed_attempts_1h{0};
    int account_age_days{-1};
    bool is_new_device{false};
    bool is_new_location{false};
};

struct RuleConfig {
    double large_amount_threshold{5000.0};
    int rapid_frequency_threshold{5};
    int failed_attempts_threshold{3};
    int minimum_account_age_days{7};
    double large_amount_contribution{0.35};
    double rapid_frequency_contribution{0.30};
    double failed_attempts_contribution{0.20};
    double new_device_contribution{0.10};
    double new_location_contribution{0.10};
    double cross_border_contribution{0.10};
    double high_risk_merchant_contribution{0.15};
    std::vector<std::string> high_risk_merchant_categories{
        "cash_advance", "crypto", "gambling"
    };
};

struct RuleResult {
    std::string rule_id;
    bool triggered{false};
    double risk_contribution{0.0};
    std::string reason;
};

struct FraudEvaluation {
    double rule_score{0.0};
    std::string risk_level{"low"};
    std::vector<RuleResult> rules;
    std::vector<std::string> reasons;
};

class FraudRules {
public:
    explicit FraudRules(RuleConfig config = {});

    FraudEvaluation evaluate(const TransactionFeatures& transaction) const;

private:
    RuleConfig config_;
};

double clampRiskScore(double score);
std::string riskLevelForScore(double score);

}  // namespace banking::fraud
