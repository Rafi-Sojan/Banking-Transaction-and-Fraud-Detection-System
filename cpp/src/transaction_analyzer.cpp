#include "transaction_analyzer.hpp"

#include <cctype>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include <utility>
#include <vector>

namespace banking::fraud {
namespace {

struct JsonValue {
    enum class Type { Null, Boolean, Number, String, Object };

    Type type{Type::Null};
    bool boolean{false};
    double number{0.0};
    std::string string;
    std::map<std::string, JsonValue> object;
};

class JsonParser {
public:
    explicit JsonParser(const std::string& input) : input_(input) {}

    JsonValue parse() {
        skipWhitespace();
        auto value = parseValue();
        skipWhitespace();
        if (position_ != input_.size()) {
            fail("unexpected characters after JSON value");
        }
        return value;
    }

private:
    std::string input_;
    std::size_t position_{0};

    [[noreturn]] void fail(const std::string& message) const {
        throw std::invalid_argument("Invalid JSON at position "
            + std::to_string(position_) + ": " + message);
    }

    void skipWhitespace() {
        while (position_ < input_.size()) {
            const auto character = static_cast<unsigned char>(input_[position_]);
            if (!std::isspace(character)) {
                break;
            }
            ++position_;
        }
    }

    bool consume(char expected) {
        skipWhitespace();
        if (position_ < input_.size() && input_[position_] == expected) {
            ++position_;
            return true;
        }
        return false;
    }

    void expect(char expected) {
        if (!consume(expected)) {
            fail(std::string("expected '") + expected + "'");
        }
    }

    JsonValue parseValue() {
        skipWhitespace();
        if (position_ >= input_.size()) {
            fail("expected a value");
        }

        switch (input_[position_]) {
        case '{':
            return parseObject();
        case '"': {
            JsonValue value;
            value.type = JsonValue::Type::String;
            value.string = parseString();
            return value;
        }
        case 't':
            consumeLiteral("true");
            return booleanValue(true);
        case 'f':
            consumeLiteral("false");
            return booleanValue(false);
        case 'n':
            consumeLiteral("null");
            return JsonValue{};
        default:
            if (input_[position_] == '-' || std::isdigit(static_cast<unsigned char>(input_[position_]))) {
                JsonValue value;
                value.type = JsonValue::Type::Number;
                value.number = parseNumber();
                return value;
            }
            fail("unsupported value");
        }
    }

    void consumeLiteral(const std::string& literal) {
        if (input_.substr(position_, literal.size()) != literal) {
            fail("invalid literal");
        }
        position_ += literal.size();
    }

    static JsonValue booleanValue(bool value) {
        JsonValue result;
        result.type = JsonValue::Type::Boolean;
        result.boolean = value;
        return result;
    }

    JsonValue parseObject() {
        JsonValue value;
        value.type = JsonValue::Type::Object;
        expect('{');
        skipWhitespace();
        if (consume('}')) {
            return value;
        }

        while (true) {
            skipWhitespace();
            if (position_ >= input_.size() || input_[position_] != '"') {
                fail("object keys must be strings");
            }
            const auto key = parseString();
            expect(':');
            value.object[key] = parseValue();
            if (consume('}')) {
                return value;
            }
            expect(',');
        }
    }

    std::string parseString() {
        expect('"');
        std::string result;
        while (position_ < input_.size()) {
            const char character = input_[position_++];
            if (character == '"') {
                return result;
            }
            if (character == '\\') {
                if (position_ >= input_.size()) {
                    fail("unterminated escape sequence");
                }
                const char escaped = input_[position_++];
                switch (escaped) {
                case '"': result.push_back('"'); break;
                case '\\': result.push_back('\\'); break;
                case '/': result.push_back('/'); break;
                case 'b': result.push_back('\b'); break;
                case 'f': result.push_back('\f'); break;
                case 'n': result.push_back('\n'); break;
                case 'r': result.push_back('\r'); break;
                case 't': result.push_back('\t'); break;
                default: fail("unsupported escape sequence");
                }
            } else {
                result.push_back(character);
            }
        }
        fail("unterminated string");
    }

    double parseNumber() {
        const auto* start = input_.data() + position_;
        char* end = nullptr;
        const double result = std::strtod(start, &end);
        if (end == start || !std::isfinite(result)) {
            fail("invalid number");
        }
        position_ += static_cast<std::size_t>(end - start);
        return result;
    }
};

const JsonValue* findValue(const JsonValue& object, const std::string& key) {
    if (object.type != JsonValue::Type::Object) {
        throw std::invalid_argument("JSON root must be an object");
    }
    const auto iterator = object.object.find(key);
    return iterator == object.object.end() ? nullptr : &iterator->second;
}

std::string requiredString(const JsonValue& object, const std::string& key) {
    const auto* value = findValue(object, key);
    if (value == nullptr || value->type != JsonValue::Type::String || value->string.empty()) {
        throw std::invalid_argument("Missing or invalid required string field: " + key);
    }
    return value->string;
}

std::string optionalString(const JsonValue& object, const std::string& key, std::string fallback = {}) {
    const auto* value = findValue(object, key);
    if (value == nullptr) {
        return fallback;
    }
    if (value->type != JsonValue::Type::String) {
        throw std::invalid_argument("Field must be a string: " + key);
    }
    return value->string;
}

double requiredNumber(const JsonValue& object, const std::string& key) {
    const auto* value = findValue(object, key);
    if (value == nullptr || value->type != JsonValue::Type::Number || !std::isfinite(value->number)) {
        throw std::invalid_argument("Missing or invalid required number field: " + key);
    }
    return value->number;
}

double optionalNumber(const JsonValue& object, const std::string& key, double fallback) {
    const auto* value = findValue(object, key);
    if (value == nullptr) {
        return fallback;
    }
    if (value->type != JsonValue::Type::Number || !std::isfinite(value->number)) {
        throw std::invalid_argument("Field must be a finite number: " + key);
    }
    return value->number;
}

int optionalInteger(const JsonValue& object, const std::string& key, int fallback) {
    const auto value = optionalNumber(object, key, static_cast<double>(fallback));
    if (std::floor(value) != value
        || value < static_cast<double>(std::numeric_limits<int>::min())
        || value > static_cast<double>(std::numeric_limits<int>::max())) {
        throw std::invalid_argument("Field must be an integer: " + key);
    }
    return static_cast<int>(value);
}

bool optionalBoolean(const JsonValue& object, const std::string& key, bool fallback) {
    const auto* value = findValue(object, key);
    if (value == nullptr) {
        return fallback;
    }
    if (value->type != JsonValue::Type::Boolean) {
        throw std::invalid_argument("Field must be boolean: " + key);
    }
    return value->boolean;
}

TransactionFeatures parseTransaction(const JsonValue& root) {
    TransactionFeatures transaction;
    transaction.transaction_id = requiredString(root, "transaction_id");
    transaction.amount = requiredNumber(root, "amount");
    transaction.transaction_type = requiredString(root, "transaction_type");
    transaction.merchant_category = optionalString(root, "merchant_category");
    transaction.country = optionalString(root, "country");
    transaction.home_country = optionalString(root, "home_country");
    transaction.transaction_count_10m = optionalInteger(root, "transaction_count_10m", 0);
    transaction.failed_attempts_1h = optionalInteger(root, "failed_attempts_1h", 0);
    transaction.account_age_days = optionalInteger(root, "account_age_days", -1);
    transaction.is_new_device = optionalBoolean(root, "is_new_device", false);
    transaction.is_new_location = optionalBoolean(root, "is_new_location", false);

    if (transaction.amount <= 0.0) {
        throw std::invalid_argument("amount must be greater than zero");
    }
    if (transaction.transaction_count_10m < 0 || transaction.failed_attempts_1h < 0
        || transaction.account_age_days < -1) {
        throw std::invalid_argument("count and age fields cannot be negative");
    }
    return transaction;
}

RuleConfig parseRuleConfig(const JsonValue& root, RuleConfig config) {
    const auto* configValue = findValue(root, "rule_config");
    if (configValue == nullptr) {
        return config;
    }
    if (configValue->type != JsonValue::Type::Object) {
        throw std::invalid_argument("rule_config must be an object");
    }
    config.large_amount_threshold = optionalNumber(*configValue, "large_amount_threshold", config.large_amount_threshold);
    config.rapid_frequency_threshold = optionalInteger(*configValue, "rapid_frequency_threshold", config.rapid_frequency_threshold);
    config.failed_attempts_threshold = optionalInteger(*configValue, "failed_attempts_threshold", config.failed_attempts_threshold);
    config.minimum_account_age_days = optionalInteger(*configValue, "minimum_account_age_days", config.minimum_account_age_days);
    config.large_amount_contribution = optionalNumber(*configValue, "large_amount_contribution", config.large_amount_contribution);
    config.rapid_frequency_contribution = optionalNumber(*configValue, "rapid_frequency_contribution", config.rapid_frequency_contribution);
    config.failed_attempts_contribution = optionalNumber(*configValue, "failed_attempts_contribution", config.failed_attempts_contribution);
    config.new_device_contribution = optionalNumber(*configValue, "new_device_contribution", config.new_device_contribution);
    config.new_location_contribution = optionalNumber(*configValue, "new_location_contribution", config.new_location_contribution);
    config.cross_border_contribution = optionalNumber(*configValue, "cross_border_contribution", config.cross_border_contribution);
    config.high_risk_merchant_contribution = optionalNumber(*configValue, "high_risk_merchant_contribution", config.high_risk_merchant_contribution);
    if (config.rapid_frequency_threshold < 1 || config.failed_attempts_threshold < 1
        || config.minimum_account_age_days < 0) {
        throw std::invalid_argument("rule_config thresholds are invalid");
    }
    return config;
}

std::string escapeJson(const std::string& value) {
    std::ostringstream output;
    for (const char character : value) {
        switch (character) {
        case '"': output << "\\\""; break;
        case '\\': output << "\\\\"; break;
        case '\b': output << "\\b"; break;
        case '\f': output << "\\f"; break;
        case '\n': output << "\\n"; break;
        case '\r': output << "\\r"; break;
        case '\t': output << "\\t"; break;
        default: output << character; break;
        }
    }
    return output.str();
}

std::string serialize(const TransactionFeatures& transaction, const FraudEvaluation& evaluation) {
    std::ostringstream output;
    output << std::fixed << std::setprecision(6);
    output << "{\"transaction_id\":\"" << escapeJson(transaction.transaction_id)
           << "\",\"rule_score\":" << evaluation.rule_score
           << ",\"risk_level\":\"" << evaluation.risk_level << "\",\"rules\":[";

    for (std::size_t index = 0; index < evaluation.rules.size(); ++index) {
        const auto& rule = evaluation.rules[index];
        if (index > 0) {
            output << ',';
        }
        output << "{\"rule_id\":\"" << escapeJson(rule.rule_id)
               << "\",\"triggered\":" << (rule.triggered ? "true" : "false")
               << ",\"risk_contribution\":" << rule.risk_contribution
               << ",\"reason\":\"" << escapeJson(rule.reason) << "\"}";
    }

    output << "],\"reasons\":[";
    for (std::size_t index = 0; index < evaluation.reasons.size(); ++index) {
        if (index > 0) {
            output << ',';
        }
        output << "\"" << escapeJson(evaluation.reasons[index]) << "\"";
    }
    output << "]}";
    return output.str();
}

}  // namespace

TransactionAnalyzer::TransactionAnalyzer(RuleConfig config) : config_(std::move(config)) {}

FraudEvaluation TransactionAnalyzer::analyze(const TransactionFeatures& transaction) const {
    return FraudRules(config_).evaluate(transaction);
}

std::string TransactionAnalyzer::analyzeJson(const std::string& input) const {
    const auto root = JsonParser(input).parse();
    const auto transaction = parseTransaction(root);
    const auto config = parseRuleConfig(root, config_);
    const auto evaluation = FraudRules(config).evaluate(transaction);
    return serialize(transaction, evaluation);
}

}  // namespace banking::fraud
