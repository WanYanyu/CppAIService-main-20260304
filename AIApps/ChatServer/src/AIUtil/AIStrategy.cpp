#include"../include/AIUtil/AIStrategy.h"
#include"../include/AIUtil/AIFactory.h"

// AliyunStrategy
std::string AliyunStrategy::getApiUrl() const {
    return "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions";
}

std::string AliyunStrategy::getModel() const {
    return "qwen-plus";
}

json AliyunStrategy::buildRequest(const std::vector<std::pair<std::string, long long>>& messages) const {
    json payload;
    payload["model"] = getModel();
    json msgArray = json::array();
    for (size_t i = 0; i < messages.size(); ++i) {
        json msg;
        msg["role"] = (i % 2 == 0) ? "user" : "assistant";
        msg["content"] = messages[i].first;
        msgArray.push_back(msg);
    }
    payload["messages"] = msgArray;
    return payload;
}

std::string AliyunStrategy::parseResponse(const json& response) const {
    if (response.contains("choices") && !response["choices"].empty()) {
        return response["choices"][0]["message"]["content"];
    }
    return {};
}

// DouBaoStrategy
std::string DouBaoStrategy::getApiUrl()const {
    return "https://ark.cn-beijing.volces.com/api/v3/chat/completions";
}

std::string DouBaoStrategy::getModel() const {
    return "doubao-pro-32k"; // Updated to a standard model name
}

json DouBaoStrategy::buildRequest(const std::vector<std::pair<std::string, long long>>& messages) const {
    json payload;
    payload["model"] = getModel();
    json msgArray = json::array();
    for (size_t i = 0; i < messages.size(); ++i) {
        json msg;
        msg["role"] = (i % 2 == 0) ? "user" : "assistant";
        msg["content"] = messages[i].first;
        msgArray.push_back(msg);
    }
    payload["messages"] = msgArray;
    return payload;
}

std::string DouBaoStrategy::parseResponse(const json& response) const {
    if (response.contains("choices") && !response["choices"].empty()) {
        return response["choices"][0]["message"]["content"];
    }
    return {};
}

// DeepseekStrategy
std::string DeepseekStrategy::getApiUrl() const {
    return "https://api.deepseek.com/chat/completions";
}
std::string DeepseekStrategy::getModel() const { return "deepseek-chat"; }
json DeepseekStrategy::buildRequest(const std::vector<std::pair<std::string, long long>>& messages) const {
    json payload;
    payload["model"] = getModel();
    json msgArray = json::array();
    for (size_t i = 0; i < messages.size(); ++i) {
        json msg;
        msg["role"] = (i % 2 == 0) ? "user" : "assistant";
        msg["content"] = messages[i].first;
        msgArray.push_back(msg);
    }
    payload["messages"] = msgArray;
    return payload;
}
std::string DeepseekStrategy::parseResponse(const json& response) const {
    if (response.contains("choices") && !response["choices"].empty()) return response["choices"][0]["message"]["content"];
    return {};
}

// OpenAIStrategy
std::string OpenAIStrategy::getApiUrl() const { return "https://api.openai.com/v1/chat/completions"; }
std::string OpenAIStrategy::getModel() const { return "gpt-4o"; }
json OpenAIStrategy::buildRequest(const std::vector<std::pair<std::string, long long>>& messages) const {
    json payload;
    payload["model"] = getModel();
    json msgArray = json::array();
    for (size_t i = 0; i < messages.size(); ++i) {
        json msg;
        msg["role"] = (i % 2 == 0) ? "user" : "assistant";
        msg["content"] = messages[i].first;
        msgArray.push_back(msg);
    }
    payload["messages"] = msgArray;
    return payload;
}
std::string OpenAIStrategy::parseResponse(const json& response) const {
    if (response.contains("choices") && !response["choices"].empty()) return response["choices"][0]["message"]["content"];
    return {};
}

// GeminiStrategy
std::string GeminiStrategy::getApiUrl() const { return "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"; } // Using REST API
std::string GeminiStrategy::getModel() const { return "gemini-pro"; }
json GeminiStrategy::buildRequest(const std::vector<std::pair<std::string, long long>>& messages) const {
    // Gemini structure is different { "contents": [{ "parts": [{"text": "..."}] }] }
    json payload;
    json contents = json::array();
    for (size_t i = 0; i < messages.size(); ++i) {
        json part;
        part["text"] = messages[i].first;
        json content;
        content["role"] = (i % 2 == 0) ? "user" : "model";
        content["parts"] = json::array({part});
        contents.push_back(content);
    }
    payload["contents"] = contents;
    return payload;
}
std::string GeminiStrategy::parseResponse(const json& response) const {
    // { "candidates": [ { "content": { "parts": [ { "text": "..." } ] } } ] }
    if (response.contains("candidates") && !response["candidates"].empty()) {
        auto& candidate = response["candidates"][0];
        if (candidate.contains("content") && candidate["content"].contains("parts")) {
             return candidate["content"]["parts"][0]["text"];
        }
    }
    return {};
}

// Register
static StrategyRegister<AliyunStrategy> regAliyun("qwen");
static StrategyRegister<AliyunStrategy> regAliyunPlus("qwen-plus"); // Alias

static StrategyRegister<DouBaoStrategy> regDoubao("doubao");
static StrategyRegister<DouBaoStrategy> regDoubaoPro("doubao-pro-32k"); // Alias

static StrategyRegister<DeepseekStrategy> regDeepseek("deepseek");
static StrategyRegister<DeepseekStrategy> regDeepseekChat("deepseek-chat"); // Alias

static StrategyRegister<OpenAIStrategy> regOpenAI("openai");
static StrategyRegister<GeminiStrategy> regGemini("gemini");