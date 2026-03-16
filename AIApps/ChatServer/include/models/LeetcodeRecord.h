#pragma once
#include <string>
#include <nlohmann/json.hpp>

namespace http {
namespace model {

struct LeetcodeRecord {
    long long id = 0;
    long long user_id = 0;
    int problem_id = 0;
    std::string problem_title;
    std::string difficulty;
    int stage = 0;
    long long last_review_time = 0;
    long long next_review_time = 0;
    int status = 0;

    NLOHMANN_DEFINE_TYPE_INTRUSIVE(LeetcodeRecord, id, user_id, problem_id, problem_title, difficulty, stage, last_review_time, next_review_time, status)
};

} // namespace model
} // namespace http
