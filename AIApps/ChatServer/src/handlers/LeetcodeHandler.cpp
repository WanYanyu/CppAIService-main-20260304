#include "../../include/handlers/LeetcodeHandler.h"
#include "../../include/models/LeetcodeRecord.h"
#include "../../../HttpServer/include/http/HttpResponse.h"
#include "../../../ChatServer/include/AIUtil/AIHelper.h"
#include <chrono>
#include <ctime>
#include <sstream>
#include <vector>
#include <iostream>
#include <fstream>
#include <regex>

using namespace http;
using namespace http::model;
using json = nlohmann::json;

// ================= LeetcodeProblemHandler =================
void LeetcodeProblemHandler::handle(const http::HttpRequest &req, http::HttpResponse *resp)
{
    LOG_INFO << "LeetcodeProblemHandler::handle called";
    if (req.method() != http::HttpRequest::kPost)
    {
        resp->setStatusCode(http::HttpResponse::k405MethodNotAllowed);
        return;
    }

    std::string body = req.getBody();
    auto jsonBody = json::parse(body, nullptr, false);
    if (jsonBody.is_discarded() || !jsonBody.contains("problemId"))
    {
        std::string err = "{\"error\":\"Invalid JSON or missing problemId\"}";
        server_->packageResp("HTTP/1.1", http::HttpResponse::k400BadRequest, "Bad Request", false, "application/json", err.length(), err, resp);
        return;
    }

    int problemId = jsonBody["problemId"];
    std::string model = jsonBody.value("model", "");

    // Ask AI for problem details
    std::string prompt = "请按JSON格式返回 Leetcode 第 " + std::to_string(problemId) + " 题的信息。\n"
                                                                                       "格式要求: {\"title\": \"英文标题\", \"difficulty\": \"Easy/Medium/Hard\", \"description\": \"中文题目描述(支持Markdown)\", \"test_cases\": \"输入输出样例\"}\n"
                                                                                       "请确保返回的是纯JSON，不要包含markdown代码块标记。";

    try
    {
        AIHelper aiHelper;
        std::string result = aiHelper.chat(0, "System", "fetch_problem", prompt, model);

        // Clean up markdown code blocks if present
        if (result.find("```json") != std::string::npos)
        {
            result = std::regex_replace(result, std::regex("```json\\s*|\\s*```"), "");
        }
        else if (result.find("```") != std::string::npos)
        {
            result = std::regex_replace(result, std::regex("```\\s*|\\s*```"), "");
        }

        // Validate JSON
        json j = json::parse(result, nullptr, false);
        if (j.is_discarded())
        {
            throw std::runtime_error("AI returned invalid JSON");
        }

        json respJson;
        respJson["code"] = 0;
        respJson["data"] = j;

        std::string respBody = respJson.dump();
        server_->packageResp("HTTP/1.1", http::HttpResponse::k200Ok, "OK", false, "application/json", respBody.length(), respBody, resp);
    }
    catch (std::exception &e)
    {
        LOG_ERROR << "Fetch Error: " << e.what();
        std::string err = "{\"code\":-1, \"msg\":\"AI Fetch Failed\"}";
        server_->packageResp("HTTP/1.1", http::HttpResponse::k500InternalServerError, "Error", false, "application/json", err.length(), err, resp);
    }
}

// ================= LeetcodeDailyHandler =================

// ================= LeetcodeDailyHandler =================

void LeetcodeDailyHandler::handle(const http::HttpRequest &req, http::HttpResponse *resp)
{
    // Allow POST for passing userId in body
    if (req.method() != http::HttpRequest::kPost)
    {
        resp->setStatusCode(http::HttpResponse::k405MethodNotAllowed);
        return;
    }

    auto jsonBody = json::parse(req.getBody(), nullptr, false);
    if (jsonBody.is_discarded() || !jsonBody.contains("userId"))
    {
        server_->packageResp("HTTP/1.1", http::HttpResponse::k400BadRequest, "Invalid JSON or missing userId", false, "application/json", 0, "{}", resp);
        return;
    }

    long long userId = jsonBody["userId"];
    long long now = std::time(nullptr);

    // Logic: fetch records where next_review_time <= now AND status = 0 (Ongoing)
    // Status 1 means Mastered, effectively done.
    std::string type = jsonBody.value("type", "daily");

    std::stringstream ss;
    if (type == "all")
    {
        ss << "SELECT * FROM study_records WHERE user_id=" << userId << " ORDER BY id DESC";
    }
    else
    {
        // Daily review logic
        ss << "SELECT * FROM study_records WHERE user_id=" << userId
           << " AND next_review_time <= " << now
           << " AND status = 0 "
           << " ORDER BY next_review_time ASC LIMIT 50";
    }

    std::string sql = ss.str();
    sql::ResultSet *res = nullptr;
    try
    {
        res = mysqlUtil_.executeQuery(sql);
        std::vector<json> records; // Using json objects directly for easier frontend consumption
        while (res->next())
        {
            json r;
            r["id"] = res->getInt64("id");
            r["user_id"] = res->getInt64("user_id");
            r["problem_id"] = res->getInt("problem_id");
            r["problem_title"] = res->getString("problem_title");
            r["difficulty"] = res->getString("difficulty");
            int stage = res->getInt("stage");
            r["stage"] = stage;
            r["last_review_time"] = res->getInt64("last_review_time");

            long long nextReview = res->getInt64("next_review_time");
            r["next_review_time"] = nextReview;

            // Calculate days overdue
            long long diff = now - nextReview;
            int daysOverdue = diff > 0 ? (diff / (24 * 3600)) : 0;
            r["overdue_days"] = daysOverdue;

            r["status"] = res->getInt("status");

            // Added missing fields
            try
            {
                r["description"] = res->getString("description");
            }
            catch (...)
            {
                r["description"] = "";
            }
            try
            {
                r["test_cases"] = res->getString("test_cases");
            }
            catch (...)
            {
                r["test_cases"] = "";
            }

            records.push_back(r);
        }
        delete res;

        json j;
        j["code"] = 0;
        j["data"] = records;

        // Also fetch ALL records stats
        std::stringstream ssAll;
        ssAll << "SELECT count(*) as total FROM study_records WHERE user_id=" << userId;
        auto resAll = mysqlUtil_.executeQuery(ssAll.str());
        if (resAll->next())
        {
            j["total_records"] = resAll->getInt("total");
        }
        delete resAll;

        std::string body = j.dump();
        server_->packageResp("HTTP/1.1", http::HttpResponse::k200Ok, "OK", false, "application/json", body.length(), body, resp);
    }
    catch (std::exception &e)
    {
        if (res)
            delete res;
        LOG_ERROR << "DB Error: " << e.what();
        server_->packageResp("HTTP/1.1", http::HttpResponse::k500InternalServerError, "Error", false, "application/json", 0, "{\"error\":\"DB Error\"}", resp);
    }
}

// ================= LeetcodeRecordHandler =================

long long LeetcodeRecordHandler::calculateNextReview(int stage, long long lastReviewTime)
{
    int days = 1;
    switch (stage)
    {
    case 0:
        days = 1;
        break;
    case 1:
        days = 2;
        break;
    case 2:
        days = 4;
        break;
    case 3:
        days = 7;
        break;
    case 4:
        days = 15;
        break;
    default:
        days = 30;
        break;
    }
    return lastReviewTime + days * 24 * 3600;
}

void LeetcodeRecordHandler::handle(const http::HttpRequest &req, http::HttpResponse *resp)
{
    LOG_INFO << "LeetcodeRecordHandler::handle called";
    if (req.method() != http::HttpRequest::kPost)
    {
        LOG_WARN << "Invalid method: " << req.method();
        resp->setStatusCode(http::HttpResponse::k405MethodNotAllowed);
        return;
    }

    std::string body = req.getBody();
    LOG_INFO << "Request Body: " << body;

    auto jsonBody = json::parse(body, nullptr, false);
    if (jsonBody.is_discarded())
    {
        LOG_ERROR << "Invalid JSON";
        std::string body = "{}";
        server_->packageResp("HTTP/1.1", http::HttpResponse::k400BadRequest, "Invalid JSON", false, "application/json", body.length(), body, resp);
        return;
    }

    if (!jsonBody.contains("userId") || !jsonBody.contains("problemId"))
    {
        LOG_ERROR << "Missing userId or problemId";
        std::string body = "{}";
        server_->packageResp("HTTP/1.1", http::HttpResponse::k400BadRequest, "Missing userId or problemId", false, "application/json", body.length(), body, resp);
        return;
    }

    long long userId = jsonBody["userId"];
    int problemId = jsonBody["problemId"];
    std::string title = jsonBody.value("title", "Unknown");
    std::string difficulty = jsonBody.value("difficulty", "Easy");
    std::string description = jsonBody.value("description", ""); // New field
    std::string testCases = jsonBody.value("test_cases", "");    // New field

    LOG_INFO << "Processing record: User=" << userId << ", Problem=" << problemId << ", Title=" << title;

    // Actions:
    // 1. New Record (default if no IsReview)
    // 2. Review - Done (IsReview=true) -> Advance stage
    // 3. Review - Mastered (IsMastered=true) -> Status=1
    // 4. Review - Forgot (IsForgot=true) -> Stage=0

    bool isReview = jsonBody.value("isReview", false);
    bool isMastered = jsonBody.value("isMastered", false);
    bool isForgot = jsonBody.value("isForgot", false);

    long long now = std::time(nullptr);

    try
    {
        // Helper for SQL escaping
        auto escapeSQL = [](const std::string &input) -> std::string
        {
            std::string output;
            output.reserve(input.size() * 1.2);
            for (char c : input)
            {
                if (c == '\'')
                    output += "\\'";
                else if (c == '\\')
                    output += "\\\\";
                else if (c == '"')
                    output += "\\\"";
                else
                    output += c;
            }
            return output;
        };

        if (!isReview)
        {
            // New Record Mode
            std::stringstream ss;
            ss << "SELECT count(*) as cnt FROM study_records WHERE user_id=" << userId << " AND problem_id=" << problemId;
            LOG_INFO << "Checking existence: " << ss.str();

            auto res = mysqlUtil_.executeQuery(ss.str());
            int count = 0;
            if (res && res->next())
            {
                count = res->getInt("cnt");
            }
            if (res)
                delete res;

            if (count > 0)
            {
                // Optimization: If it exists, update the description/test_cases if they are provided/different?
                // For now, let's update description if it was empty, or just overwrite.
                // This helps if user re-adds to get description.
                std::stringstream updateSql;
                updateSql << "UPDATE study_records SET "
                          << "description='" << escapeSQL(description) << "', "
                          << "test_cases='" << escapeSQL(testCases) << "', "
                          << "difficulty='" << escapeSQL(difficulty) << "', "
                          << "problem_title='" << escapeSQL(title) << "' "
                          << "WHERE user_id=" << userId << " AND problem_id=" << problemId;
                mysqlUtil_.executeUpdate(updateSql.str());

                std::string body = "{\"code\":0, \"msg\":\"Updated existing record\"}";
                server_->packageResp("HTTP/1.1", http::HttpResponse::k200Ok, "Updated", false, "application/json", body.length(), body, resp);
                return;
            }

            long long nextReview = now + 24 * 3600; // 1 day later

            std::stringstream insertSql;
            // Enhanced logging
            LOG_INFO << "Inserting new record. Desc length: " << description.length();

            std::string escapedDesc = escapeSQL(description);
            LOG_INFO << "Escaped Desc length: " << escapedDesc.length();

            insertSql << "INSERT INTO study_records (user_id, problem_id, problem_title, difficulty, description, test_cases, stage, last_review_time, next_review_time, status) VALUES ("
                      << userId << ", " << problemId << ", '" << escapeSQL(title) << "', '" << escapeSQL(difficulty) << "', '"
                      << escapedDesc << "', '" << escapeSQL(testCases) << "', 0, " << now << ", " << nextReview << ", 0)";

            LOG_INFO << "Execute SQL: " << insertSql.str();

            mysqlUtil_.executeUpdate(insertSql.str());
            std::string body = "{\"code\":0}";
            server_->packageResp("HTTP/1.1", http::HttpResponse::k200Ok, "Added", false, "application/json", body.length(), body, resp);
        }
        else
        {
            // Review/Update Mode
            std::stringstream query;
            query << "SELECT stage, status FROM study_records WHERE user_id=" << userId << " AND problem_id=" << problemId;
            auto res = mysqlUtil_.executeQuery(query.str());

            if (res->next())
            {
                int currentStage = res->getInt("stage");
                delete res;

                int nextStage = currentStage;
                long long nextReview = 0;
                int nextStatus = 0; // Default ongoing

                if (isMastered)
                {
                    nextStatus = 1; // Mastered
                    // Keep stage/review time as is or update?
                    // Usually if mastered, we don't need next review, but keeping data is fine.
                    nextReview = now; // Doesn't matter much if filtered out
                }
                else if (isForgot)
                {
                    nextStage = 0;                // Reset
                    nextReview = now + 24 * 3600; // Review tomorrow
                }
                else
                {
                    // Normal review done
                    nextStage = currentStage + 1;
                    nextReview = calculateNextReview(nextStage, now);
                }

                std::stringstream update;
                update << "UPDATE study_records SET stage=" << nextStage
                       << ", last_review_time=" << now
                       << ", next_review_time=" << nextReview
                       << ", status=" << nextStatus
                       << " WHERE user_id=" << userId << " AND problem_id=" << problemId;

                mysqlUtil_.executeUpdate(update.str());
                std::string body = "{\"code\":0}";
                server_->packageResp("HTTP/1.1", http::HttpResponse::k200Ok, "Reviewed", false, "application/json", body.length(), body, resp);
            }
            else
            {
                delete res;
                std::string body = "{}";
                server_->packageResp("HTTP/1.1", http::HttpResponse::k404NotFound, "Not Found", false, "application/json", body.length(), body, resp);
            }
        }
    }
    catch (std::exception &e)
    {
        LOG_ERROR << "DB Error in RecordHandler: " << e.what();
        std::string body = "{\"code\":-1}";
        server_->packageResp("HTTP/1.1", http::HttpResponse::k500InternalServerError, "DB Error", false, "application/json", body.length(), body, resp);
    }
}

// ================= LeetcodeAnalyzeHandler =================

// ================= LeetcodeAnalyzeHandler =================

void LeetcodeAnalyzeHandler::handle(const http::HttpRequest &req, http::HttpResponse *resp)
{
    LOG_INFO << "LeetcodeAnalyzeHandler::handle called";
    if (req.method() != http::HttpRequest::kPost)
    {
        resp->setStatusCode(http::HttpResponse::k405MethodNotAllowed);
        return;
    }

    std::string body = req.getBody();
    LOG_INFO << "Analyze request body size: " << body.size();

    auto jsonBody = json::parse(body, nullptr, false);
    if (jsonBody.is_discarded())
    {
        std::string errBody = "{\"error\":\"Invalid JSON\"}";
        server_->packageResp("HTTP/1.1", http::HttpResponse::k400BadRequest, "Invalid JSON", false, "application/json", errBody.length(), errBody, resp);
        return;
    }

    std::string code = jsonBody.value("code", "");
    std::string problem = jsonBody.value("problem", "");
    std::string error = jsonBody.value("error", "");
    std::string model = jsonBody.value("model", "");      // Allow frontend to specify model
    std::string mode = jsonBody.value("mode", "analyze"); // "analyze" or "judge"

    std::string prompt;
    if (mode == "judge")
    {
        prompt = "请作为 Leetcode 判题机。\n题目: " + problem + "\n\n用户代码:\n" + code +
                 "\n\n请严格判断该代码是否正确。如果正确，请返回: {\"pass\": true, \"feedback\": \"通过...\"}\n"
                 "如果错误，请返回: {\"pass\": false, \"feedback\": \"错误原因...\"}\n"
                 "只返回JSON格式，不要Markdown。";
    }
    else
    {
        prompt = "请帮我分析我的 Leetcode C++ 解法。\n题目描述: " + problem + "\n\n我的代码:\n" + code;
        if (!error.empty())
        {
            prompt += "\n\n错误信息/Wrong Answer: " + error;
        }
        prompt += "\n\n请给出分析（时间/空间复杂度）和修正后的代码（如果需要修正）。";
    }

    try
    {
        AIHelper aiHelper;
        // Using userId=0 for temporary analysis session, sessionId="analysis_temp"
        std::string result = aiHelper.chat(0, "User", "analysis_temp", prompt, model);

        json j;
        j["code"] = 0;

        if (mode == "judge")
        {
            // Clean up markdown
            if (result.find("```json") != std::string::npos)
            {
                result = std::regex_replace(result, std::regex("```json\\s*|\\s*```"), "");
            }
            else if (result.find("```") != std::string::npos)
            {
                result = std::regex_replace(result, std::regex("```\\s*|\\s*```"), "");
            }
            try
            {
                json judgeRes = json::parse(result);
                j["judge"] = judgeRes;
            }
            catch (...)
            {
                j["judge"] = {{"pass", false}, {"feedback", "AI返回格式错误: " + result}};
            }
        }
        else
        {
            j["analysis"] = result;
        }

        std::string body = j.dump();
        server_->packageResp("HTTP/1.1", http::HttpResponse::k200Ok, "OK", false, "application/json", body.length(), body, resp);
    }
    catch (std::exception &e)
    {
        LOG_ERROR << "AI Error: " << e.what();
        std::string errBody = "{\"code\":-1, \"msg\":\"AI Service Error\"}";
        server_->packageResp("HTTP/1.1", http::HttpResponse::k500InternalServerError, "AI Error", false, "application/json", errBody.length(), errBody, resp);
    }
}

// ================= LeetcodePageHandler =================

void LeetcodePageHandler::handle(const http::HttpRequest &req, http::HttpResponse *resp)
{
    if (req.method() != http::HttpRequest::kGet)
    {
        resp->setStatusCode(http::HttpResponse::k405MethodNotAllowed);
        return;
    }

    // Try to locate resource/leetcode_app.html
    std::string path = "../AIApps/ChatServer/resource/leetcode_app.html"; // Default for build dir
    std::ifstream file(path);
    if (!file.is_open())
    {
        path = "AIApps/ChatServer/resource/leetcode_app.html"; // From root
        file.open(path);
    }
    if (!file.is_open())
    {
        path = "resource/leetcode_app.html"; // Fallback
        file.open(path);
    }

    if (file.is_open())
    {
        LOG_INFO << "Serving Leetcode page from: " << path;
        std::stringstream buffer;
        buffer << file.rdbuf();
        std::string content = buffer.str();
        server_->packageResp("HTTP/1.1", http::HttpResponse::k200Ok, "OK", false, "text/html", content.length(), content, resp);
    }
    else
    {
        LOG_ERROR << "Failed to find leetcode.html in any search path";
        std::string errBody = "404 Not Found: leetcode.html missing";
        server_->packageResp("HTTP/1.1", http::HttpResponse::k404NotFound, "Not Found", false, "text/html", errBody.length(), errBody, resp);
    }
}

// ================= Agent Handlers Helpers =================
static size_t AgentWriteCallback(void *contents, size_t size, size_t nmemb, void *userp)
{
    size_t totalSize = size * nmemb;
    std::string *buffer = static_cast<std::string *>(userp);
    buffer->append(static_cast<char *>(contents), totalSize);
    return totalSize;
}

static std::string postToAgent(const std::string &url, const std::string &payloadStr)
{
    CURL *curl = curl_easy_init();
    if (!curl)
        return "{\"error\": \"curl init failed\"}";

    std::string readBuffer;
    struct curl_slist *headers = nullptr;
    headers = curl_slist_append(headers, "Content-Type: application/json");

    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, payloadStr.c_str());
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, AgentWriteCallback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &readBuffer);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 60L); // 60s timeout for agents

    CURLcode res = curl_easy_perform(curl);
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);

    if (res != CURLE_OK)
    {
        LOG_ERROR << "Agent request failed: " << curl_easy_strerror(res);
        return "{\"error\": \"Agent request failed\"}";
    }
    return readBuffer;
}

// ================= LeetcodeSandboxHandler =================
void LeetcodeSandboxHandler::handle(const http::HttpRequest &req, http::HttpResponse *resp)
{
    if (req.method() != http::HttpRequest::kPost)
    {
        resp->setStatusCode(http::HttpResponse::k405MethodNotAllowed);
        return;
    }

    std::string body = req.getBody();
    auto jsonBody = json::parse(body, nullptr, false);
    if (jsonBody.is_discarded())
    {
        std::string errBody = "{\"error\":\"Invalid JSON\"}";
        server_->packageResp("HTTP/1.1", http::HttpResponse::k400BadRequest, "Invalid JSON", false, "application/json", errBody.length(), errBody, resp);
        return;
    }

    // Build payload for Sandbox (8001)
    json sandboxReq;
    sandboxReq["language"] = jsonBody.value("language", "cpp"); // default to cpp
    sandboxReq["code"] = jsonBody.value("code", "");

    // Provide generic test cases if none sent
    if (jsonBody.contains("test_cases") && jsonBody["test_cases"].is_array())
    {
        sandboxReq["test_cases"] = jsonBody["test_cases"];
    }
    else
    {
        sandboxReq["test_cases"] = json::array({{{"input", ""}, {"expected_output", ""}}});
    }

    std::string agentResponse = postToAgent("http://127.0.0.1:8002/api/sandbox/evaluate", sandboxReq.dump());

    // Forward the python agent JSON straight to frontend
    // Sandbox returns {status, stdout_log, stderr_log, ai_feedback}
    server_->packageResp("HTTP/1.1", http::HttpResponse::k200Ok, "OK", false, "application/json", agentResponse.length(), agentResponse, resp);
}

// ================= LeetcodeTutorHandler =================
void LeetcodeTutorHandler::handle(const http::HttpRequest &req, http::HttpResponse *resp)
{
    if (req.method() != http::HttpRequest::kPost)
    {
        resp->setStatusCode(http::HttpResponse::k405MethodNotAllowed);
        return;
    }

    std::string body = req.getBody();
    auto jsonBody = json::parse(body, nullptr, false);
    if (jsonBody.is_discarded())
    {
        std::string errBody = "{\"error\":\"Invalid JSON\"}";
        server_->packageResp("HTTP/1.1", http::HttpResponse::k400BadRequest, "Invalid JSON", false, "application/json", errBody.length(), errBody, resp);
        return;
    }

    // Pass raw JSON via Post to 8000
    // Expected to have problem_id, problem_description, current_code, chat_history, user_message
    std::string agentResponse = postToAgent("http://127.0.0.1:8001/api/tutor/chat", body);

    // Forward response straight to frontend
    server_->packageResp("HTTP/1.1", http::HttpResponse::k200Ok, "OK", false, "application/json", agentResponse.length(), agentResponse, resp);
}

// ================= LeetcodeTutorHistorySaveHandler =================
void LeetcodeTutorHistorySaveHandler::handle(const http::HttpRequest &req, http::HttpResponse *resp)
{
    if (req.method() != http::HttpRequest::kPost && req.method() != http::HttpRequest::kOptions)
    {
        resp->setStatusCode(http::HttpResponse::k405MethodNotAllowed);
        return;
    }

    if (req.method() == http::HttpRequest::kOptions)
    {
        server_->packageResp("HTTP/1.1", http::HttpResponse::k200Ok, "OK", false, "text/plain", 0, "", resp);
        return;
    }

    std::string body = req.getBody();
    auto jsonBody = json::parse(body, nullptr, false);
    if (jsonBody.is_discarded() || !jsonBody.contains("user_id") || !jsonBody.contains("problem_id") || !jsonBody.contains("chat_history"))
    {
        std::string errBody = "{\"code\": -1, \"msg\": \"Invalid JSON or missing fields\"}";
        server_->packageResp("HTTP/1.1", http::HttpResponse::k400BadRequest, "Bad Request", false, "application/json", errBody.length(), errBody, resp);
        return;
    }

    long long userId = jsonBody["user_id"];
    int problemId = jsonBody["problem_id"];
    std::string chatHistoryStr;

    // The chat_history might be passed as object or array
    if (jsonBody["chat_history"].is_string())
    {
        chatHistoryStr = jsonBody["chat_history"];
    }
    else
    {
        chatHistoryStr = jsonBody["chat_history"].dump();
    }

    // Escape single quotes for SQL
    std::string escapedHistory;
    for (char c : chatHistoryStr)
    {
        if (c == '\'')
            escapedHistory += "\\'";
        else if (c == '\\')
            escapedHistory += "\\\\";
        else
            escapedHistory += c;
    }

    std::string updateSql = "UPDATE study_records SET tutor_chat_history = '" + escapedHistory +
                            "' WHERE user_id = " + std::to_string(userId) + " AND problem_id = " + std::to_string(problemId);

    try
    {
        mysqlUtil_.executeUpdate(updateSql);
        std::string successBody = "{\"code\": 0, \"msg\": \"success\"}";
        server_->packageResp("HTTP/1.1", http::HttpResponse::k200Ok, "OK", false, "application/json", successBody.length(), successBody, resp);
    }
    catch (const std::exception &e)
    {
        LOG_ERROR << "Failed to save tutor chat history: " << e.what();
        std::string errBody = "{\"code\": -1, \"msg\": \"Database error\"}";
        server_->packageResp("HTTP/1.1", http::HttpResponse::k500InternalServerError, "DB Error", false, "application/json", errBody.length(), errBody, resp);
    }
}

// ================= LeetcodeTutorHistoryGetHandler =================
void LeetcodeTutorHistoryGetHandler::handle(const http::HttpRequest &req, http::HttpResponse *resp)
{
    if (req.method() != http::HttpRequest::kPost)
    { // Can be a post or get, frontend usually posts JSON body
        resp->setStatusCode(http::HttpResponse::k405MethodNotAllowed);
        return;
    }

    std::string body = req.getBody();
    auto jsonBody = json::parse(body, nullptr, false);
    if (jsonBody.is_discarded() || !jsonBody.contains("user_id") || !jsonBody.contains("problem_id"))
    {
        std::string errBody = "{\"code\": -1, \"msg\": \"Invalid JSON or missing fields\"}";
        server_->packageResp("HTTP/1.1", http::HttpResponse::k400BadRequest, "Bad Request", false, "application/json", errBody.length(), errBody, resp);
        return;
    }

    long long userId = jsonBody["user_id"];
    int problemId = jsonBody["problem_id"];

    std::string selectSql = "SELECT tutor_chat_history FROM study_records WHERE user_id = " + std::to_string(userId) +
                            " AND problem_id = " + std::to_string(problemId) + " LIMIT 1";

    try
    {
        sql::ResultSet *result = mysqlUtil_.executeQuery(selectSql);

        std::string chatHistoryStr = "[]";
        if (result->next())
        {
            std::string dbVal = result->getString("tutor_chat_history");
            if (!dbVal.empty())
            {
                chatHistoryStr = dbVal;
            }
        }
        delete result;

        json responseObj;
        responseObj["code"] = 0;
        responseObj["msg"] = "success";

        // Return as parsed JSON array if possible
        json parsedHistory;
        try
        {
            parsedHistory = json::parse(chatHistoryStr);
            responseObj["chat_history"] = parsedHistory;
        }
        catch (...)
        {
            responseObj["chat_history"] = json::array();
        }

        std::string respBody = responseObj.dump();
        server_->packageResp("HTTP/1.1", http::HttpResponse::k200Ok, "OK", false, "application/json", respBody.length(), respBody, resp);
    }
    catch (const std::exception &e)
    {
        LOG_ERROR << "Failed to read tutor chat history: " << e.what();
        std::string errBody = "{\"code\": -1, \"msg\": \"Database error\"}";
        server_->packageResp("HTTP/1.1", http::HttpResponse::k500InternalServerError, "DB Error", false, "application/json", errBody.length(), errBody, resp);
    }
}
