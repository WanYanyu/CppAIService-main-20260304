#pragma once
#include <string>
#include <vector>
#include <utility>
#include <iostream>
#include <sstream>
#include <memory>

#include "../../../../HttpServer/include/utils/JsonUtil.h"



class AIStrategy {
public:
    virtual ~AIStrategy() = default;

    virtual std::string getApiUrl() const = 0;

    // API Key
    virtual std::string getApiKey() const { return apiKey_; }
    virtual void setApiKey(const std::string& key) { apiKey_ = key; }

    virtual std::string getModel() const = 0;

    virtual json buildRequest(const std::vector<std::pair<std::string, long long>>& messages) const = 0;

    virtual std::string parseResponse(const json& response) const = 0;

    bool isMCPModel = false;

protected:
    std::string apiKey_;
};

class AliyunStrategy : public AIStrategy {
public:
    AliyunStrategy() {
        // AIHelper responsibility to set key
        isMCPModel = false;
    }

    std::string getApiUrl() const override;
    std::string getModel() const override;
    json buildRequest(const std::vector<std::pair<std::string, long long>>& messages) const override;
    std::string parseResponse(const json& response) const override;
};

class DouBaoStrategy : public AIStrategy {
public:
    DouBaoStrategy() {
        isMCPModel = false;
    }
    std::string getApiUrl() const override;
    std::string getModel() const override;
    json buildRequest(const std::vector<std::pair<std::string, long long>>& messages) const override;
    std::string parseResponse(const json& response) const override;
};

class DeepseekStrategy : public AIStrategy {
public:
    DeepseekStrategy() { isMCPModel = false; }
    std::string getApiUrl() const override;
    std::string getModel() const override;
    json buildRequest(const std::vector<std::pair<std::string, long long>>& messages) const override;
    std::string parseResponse(const json& response) const override;
};

class OpenAIStrategy : public AIStrategy {
public:
    OpenAIStrategy() { isMCPModel = false; }
    std::string getApiUrl() const override;
    std::string getModel() const override;
    json buildRequest(const std::vector<std::pair<std::string, long long>>& messages) const override;
    std::string parseResponse(const json& response) const override;
};

class GeminiStrategy : public AIStrategy {
public:
    GeminiStrategy() { isMCPModel = false; }
    std::string getApiUrl() const override;
    std::string getModel() const override;
    json buildRequest(const std::vector<std::pair<std::string, long long>>& messages) const override;
    std::string parseResponse(const json& response) const override;
};







