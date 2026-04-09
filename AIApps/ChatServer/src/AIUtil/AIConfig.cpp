#include "../include/AIUtil/AIConfig.h"

#include <sstream>

namespace {
std::string trimCopy(const std::string& s) {
    const char* spaces = " \t\r\n";
    size_t start = s.find_first_not_of(spaces);
    if (start == std::string::npos)
        return "";
    size_t end = s.find_last_not_of(spaces);
    return s.substr(start, end - start + 1);
}

std::string readFromDotEnv(const std::string& envKey) {
    const std::vector<std::string> candidates = {
        "./Agent/.env",
        "../Agent/.env",
        "../../Agent/.env"};

    for (const auto& path : candidates) {
        std::ifstream in(path);
        if (!in.is_open())
            continue;

        std::string line;
        while (std::getline(in, line)) {
            line = trimCopy(line);
            if (line.empty() || line[0] == '#')
                continue;

            auto pos = line.find('=');
            if (pos == std::string::npos)
                continue;

            std::string key = trimCopy(line.substr(0, pos));
            if (key != envKey)
                continue;

            std::string value = trimCopy(line.substr(pos + 1));
            if (value.size() >= 2) {
                if ((value.front() == '"' && value.back() == '"') ||
                    (value.front() == '\'' && value.back() == '\'')) {
                    value = value.substr(1, value.size() - 2);
                }
            }
            return value;
        }
    }

    return "";
}
}  // namespace

bool AIConfig::loadFromFile(const std::string& path) {
    std::ifstream file(path);
    if (!file.is_open()) {
        std::cerr << "[AIConfig] Unable to open configuration file: " << path << std::endl;
        return false;
    }

    json j;
    file >> j;

    // Parsing templates
    if (!j.contains("prompt_template") || !j["prompt_template"].is_string()) {
        std::cerr << "[AIConfig] prompt_template is missing" << std::endl;
        return false;
    }
    promptTemplate_ = j["prompt_template"].get<std::string>();

    if (j.contains("default_model") && j["default_model"].is_string()) {
        defaultModel_ = j["default_model"].get<std::string>();
    }

    if (j.contains("api_keys") && j["api_keys"].is_object()) {
        for (auto& [key, val] : j["api_keys"].items()) {
            apiKeys_[key] = val.get<std::string>();
        }
    }

    // List of parsing tools
    if (j.contains("tools") && j["tools"].is_array()) {
        for (auto& tool : j["tools"]) {
            AITool t;
            t.name = tool.value("name", "");
            t.desc = tool.value("desc", "");
            if (tool.contains("params") && tool["params"].is_object()) {
                for (auto& [key, val] : tool["params"].items()) {
                    t.params[key] = val.get<std::string>();
                }
            }
            tools_.push_back(std::move(t));
        }
    }
    return true;
}

std::string AIConfig::getApiKey(const std::string& provider) const {
    // 优先从 config.json 里读取 (保持向后兼容)
    if (apiKeys_.find(provider) != apiKeys_.end() && !apiKeys_.at(provider).empty()) {
        return apiKeys_.at(provider);
    }

    // Fallback: 从系统环境变量中读取
    // 将 provider 名称映射到环境变量名 (规范：全大写 + _API_KEY)
    static const std::unordered_map<std::string, std::string> providerEnvMap = {
        {"deepseek", "DEEPSEEK_API_KEY"},
        {"deepseek-chat", "DEEPSEEK_API_KEY"},
        {"qwen", "ALIYUN_API_KEY"},
        {"qwen-plus", "ALIYUN_API_KEY"},
        {"doubao", "DOUBAO_API_KEY"},
        {"doubao-pro-32k", "DOUBAO_API_KEY"},
        {"openai", "OPENAI_API_KEY"},
        {"gemini", "GEMINI_API_KEY"},
    };

    auto it = providerEnvMap.find(provider);
    if (it != providerEnvMap.end()) {
        const char* envVal = std::getenv(it->second.c_str());
        if (envVal && *envVal) {
            std::cout << "[AIConfig] Loaded key for '" << provider << "' from env: " << it->second << std::endl;
            return std::string(envVal);
        }

        // Fallback: read from Agent/.env (for processes started without exported env vars)
        std::string dotenvVal = readFromDotEnv(it->second);
        if (!dotenvVal.empty()) {
            std::cout << "[AIConfig] Loaded key for '" << provider << "' from .env file: " << it->second << std::endl;
            return dotenvVal;
        }
    }

    return "";
}

std::string AIConfig::getDefaultModel() const {
    return defaultModel_;
}

std::string AIConfig::buildToolList() const {
    std::ostringstream oss;
    for (const auto& t : tools_) {
        oss << t.name << "(";
        bool first = true;
        for (const auto& [key, val] : t.params) {
            if (!first)
                oss << ", ";
            oss << key;
            first = false;
        }
        oss << ") -> " << t.desc << "\n";
    }
    return oss.str();
}

std::string AIConfig::buildPrompt(const std::string& userInput) const {
    std::string result = promptTemplate_;
    result = std::regex_replace(result, std::regex("\\{user_input\\}"), userInput);
    result = std::regex_replace(result, std::regex("\\{tool_list\\}"), buildToolList());
    return result;
}

AIToolCall AIConfig::parseAIResponse(const std::string& response) const {
    AIToolCall result;
    try {
        // Try parsing as JSON
        json j = json::parse(response);

        if (j.contains("tool") && j["tool"].is_string()) {
            result.toolName = j["tool"].get<std::string>();
            if (j.contains("args") && j["args"].is_object()) {
                result.args = j["args"];
            }
            result.isToolCall = true;
        }
    } catch (...) {
        // Not JSON, directly return text response
        result.isToolCall = false;
    }
    return result;
}

std::string AIConfig::buildToolResultPrompt(
    const std::string& userInput,
    const std::string& toolName,
    const json& toolArgs,
    const json& toolResult) const {
    std::ostringstream oss;
    oss << "下面是用户说的话：" << userInput << "\n"
        << "我刚才调用了工具 [" << toolName << "] ，参数为："
        << toolArgs.dump() << "\n"
        << "工具返回的结果如下：\n"
        << toolResult.dump(4) << "\n"
        << "请根据以上信息，用自然语言回答用户。";
    return oss.str();
}
