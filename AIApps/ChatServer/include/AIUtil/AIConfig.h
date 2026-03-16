#pragma once
#include <string>
#include <unordered_map>
#include <vector>
#include <regex>
#include <fstream>
#include <sstream>
#include <iostream>
#include <cstdlib> // for std::getenv
#include "../../../../HttpServer/include/utils/JsonUtil.h"

struct AITool
{
    std::string name;
    std::unordered_map<std::string, std::string> params;
    std::string desc;
};

struct AIToolCall
{
    std::string toolName;
    json args;
    bool isToolCall = false;
};

class AIConfig
{
public:
    bool loadFromFile(const std::string &path);
    std::string buildPrompt(const std::string &userInput) const;
    AIToolCall parseAIResponse(const std::string &response) const;
    std::string buildToolResultPrompt(const std::string &userInput, const std::string &toolName, const json &toolArgs, const json &toolResult) const;

    std::string getApiKey(const std::string &provider) const;
    std::string getDefaultModel() const;

private:
    std::string promptTemplate_;
    std::vector<AITool> tools_;
    std::unordered_map<std::string, std::string> apiKeys_;
    std::string defaultModel_;

    std::string buildToolList() const;
};
