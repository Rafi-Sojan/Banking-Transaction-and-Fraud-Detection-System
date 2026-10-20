#include "transaction_analyzer.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void testLowRiskTransaction() {
    banking::fraud::TransactionFeatures transaction;
    transaction.transaction_id = "test-low-risk";
    transaction.amount = 25.0;
    transaction.transaction_type = "card_purchase";
    transaction.account_age_days = 365;

    const auto evaluation = banking::fraud::TransactionAnalyzer().analyze(transaction);
    require(evaluation.risk_level == "low", "Expected low-risk transaction");
    require(std::abs(evaluation.rule_score) < 0.000001, "Expected zero rule score");
    require(evaluation.reasons.empty(), "Low-risk transaction should have no reasons");
}

void testMultipleRulesAccumulate() {
    banking::fraud::TransactionFeatures transaction;
    transaction.transaction_id = "test-high-risk";
    transaction.amount = 7500.0;
    transaction.transaction_type = "card_purchase";
    transaction.merchant_category = "crypto";
    transaction.transaction_count_10m = 6;
    transaction.failed_attempts_1h = 3;
    transaction.is_new_device = true;
    transaction.is_new_location = true;
    transaction.country = "GB";
    transaction.home_country = "IN";
    transaction.account_age_days = 2;

    const auto evaluation = banking::fraud::TransactionAnalyzer().analyze(transaction);
    require(evaluation.risk_level == "critical", "Expected critical risk for multiple triggered rules");
    require(evaluation.rule_score > 0.85, "Expected accumulated risk score above critical threshold");
    require(evaluation.reasons.size() >= 7, "Expected reasons for all triggered rules");
}

void testJsonContract() {
    const std::string input = R"({
        "transaction_id": "json-test",
        "amount": 7500,
        "transaction_type": "card_purchase",
        "transaction_count_10m": 6
    })";

    const auto output = banking::fraud::TransactionAnalyzer().analyzeJson(input);
    require(output.find("\"transaction_id\":\"json-test\"") != std::string::npos,
        "JSON output is missing transaction_id");
    require(output.find("\"risk_level\":\"high\"") != std::string::npos,
        "JSON output is missing expected risk level");
    require(output.find("\"rule_id\":\"large_amount\"") != std::string::npos,
        "JSON output is missing rule result");
}

void testInvalidJsonIsRejected() {
    bool rejected = false;
    try {
        banking::fraud::TransactionAnalyzer().analyzeJson(R"({"amount": 10})");
    } catch (const std::invalid_argument&) {
        rejected = true;
    }
    require(rejected, "Invalid JSON input should be rejected");
}

}  // namespace

int main() {
    try {
        testLowRiskTransaction();
        testMultipleRulesAccumulate();
        testJsonContract();
        testInvalidJsonIsRejected();
        std::cout << "fraud_engine_tests: all tests passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "fraud_engine_tests: " << error.what() << '\n';
        return 1;
    }
}
