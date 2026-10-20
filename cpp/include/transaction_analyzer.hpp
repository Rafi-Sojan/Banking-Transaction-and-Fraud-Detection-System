#pragma once

#include "fraud_rules.hpp"

#include <string>

namespace banking::fraud {

class TransactionAnalyzer {
public:
    explicit TransactionAnalyzer(RuleConfig config = {});

    FraudEvaluation analyze(const TransactionFeatures& transaction) const;

    // Parses one JSON object and returns one JSON object. Exceptions indicate
    // malformed input or missing/invalid required fields.
    std::string analyzeJson(const std::string& input) const;

private:
    RuleConfig config_;
};

}  // namespace banking::fraud
