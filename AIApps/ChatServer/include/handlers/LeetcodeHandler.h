#pragma once

#include "../../../HttpServer/include/router/RouterHandler.h"
#include "../../../HttpServer/include/utils/MysqlUtil.h"
#include "../ChatServer.h"
#include "../../../HttpServer/include/utils/JsonUtil.h"
#include <memory>
#include <ctime>

// Handler for fetching daily review list
class LeetcodeDailyHandler : public http::router::RouterHandler
{
public:
    LeetcodeDailyHandler(ChatServer *server, http::MysqlUtil &util) : server_(server), mysqlUtil_(util) {}
    void handle(const http::HttpRequest &req, http::HttpResponse *resp) override;

private:
    ChatServer *server_;
    http::MysqlUtil &mysqlUtil_;
};

// Handler for adding/updating study records
class LeetcodeRecordHandler : public http::router::RouterHandler
{
public:
    LeetcodeRecordHandler(ChatServer *server, http::MysqlUtil &util) : server_(server), mysqlUtil_(util) {}
    void handle(const http::HttpRequest &req, http::HttpResponse *resp) override;

private:
    ChatServer *server_;
    http::MysqlUtil &mysqlUtil_;

    long long calculateNextReview(int stage, long long lastReviewTime);
};

// Handler for AI error analysis
class LeetcodeAnalyzeHandler : public http::router::RouterHandler
{
public:
    explicit LeetcodeAnalyzeHandler(ChatServer *server) : server_(server) {}
    void handle(const http::HttpRequest &req, http::HttpResponse *resp) override;

private:
    ChatServer *server_;
};

// Handler for fetching problem details from AI
class LeetcodeProblemHandler : public http::router::RouterHandler
{
public:
    explicit LeetcodeProblemHandler(ChatServer *server) : server_(server) {}
    void handle(const http::HttpRequest &req, http::HttpResponse *resp) override;

private:
    ChatServer *server_;
};

// Handler for serving the HTML page
class LeetcodePageHandler : public http::router::RouterHandler
{
public:
    explicit LeetcodePageHandler(ChatServer *server) : server_(server) {}
    void handle(const http::HttpRequest &req, http::HttpResponse *resp) override;

private:
    ChatServer *server_;
};

// Handler for Python SandBox Agent
class LeetcodeSandboxHandler : public http::router::RouterHandler
{
public:
    explicit LeetcodeSandboxHandler(ChatServer *server) : server_(server) {}
    void handle(const http::HttpRequest &req, http::HttpResponse *resp) override;

private:
    ChatServer *server_;
};

// Handler for Python Tutor Agent
class LeetcodeTutorHandler : public http::router::RouterHandler
{
public:
    explicit LeetcodeTutorHandler(ChatServer *server) : server_(server) {}
    void handle(const http::HttpRequest &req, http::HttpResponse *resp) override;

private:
    ChatServer *server_;
};

// Handler for saving Tutor Chat History
class LeetcodeTutorHistorySaveHandler : public http::router::RouterHandler
{
public:
    LeetcodeTutorHistorySaveHandler(ChatServer *server, http::MysqlUtil &util) : server_(server), mysqlUtil_(util) {}
    void handle(const http::HttpRequest &req, http::HttpResponse *resp) override;

private:
    ChatServer *server_;
    http::MysqlUtil &mysqlUtil_;
};

// Handler for getting Tutor Chat History
class LeetcodeTutorHistoryGetHandler : public http::router::RouterHandler
{
public:
    LeetcodeTutorHistoryGetHandler(ChatServer *server, http::MysqlUtil &util) : server_(server), mysqlUtil_(util) {}
    void handle(const http::HttpRequest &req, http::HttpResponse *resp) override;

private:
    ChatServer *server_;
    http::MysqlUtil &mysqlUtil_;
};
