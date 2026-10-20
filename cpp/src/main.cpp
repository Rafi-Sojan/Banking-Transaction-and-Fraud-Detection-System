#include "transaction_analyzer.hpp"

#include <iostream>
#include <iterator>
#include <string>

int main() {
    const std::string input(
        std::istreambuf_iterator<char>(std::cin),
        std::istreambuf_iterator<char>()
    );

    if (input.empty()) {
        std::cerr << "fraud_engine error: expected one JSON object on stdin\n";
        return 2;
    }

    try {
        banking::fraud::TransactionAnalyzer analyzer;
        std::cout << analyzer.analyzeJson(input) << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "fraud_engine error: " << error.what() << '\n';
        return 2;
    }
}
