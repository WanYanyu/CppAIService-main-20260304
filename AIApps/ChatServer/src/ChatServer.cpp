#include "../include/handlers/ChatLoginHandler.h"
#include "../include/handlers/ChatRegisterHandler.h"
#include "../include/handlers/ChatLogoutHandler.h"
#include "../include/handlers/ChatHandler.h"
#include "../include/handlers/ChatEntryHandler.h"
#include "../include/handlers/ChatSendHandler.h"
#include "../include/handlers/AIMenuHandler.h"
#include "../include/handlers/AIUploadSendHandler.h"
#include "../include/handlers/AIUploadHandler.h"
#include "../include/handlers/ChatHistoryHandler.h"

#include "../include/handlers/ChatCreateAndSendHandler.h"
#include "../include/handlers/ChatSessionsHandler.h"
#include "../include/handlers/ChatSpeechHandler.h"
#include "../include/handlers/LeetcodeHandler.h"

#include "../include/ChatServer.h"
#include "../../../HttpServer/include/http/HttpRequest.h"
#include "../../../HttpServer/include/http/HttpResponse.h"
#include "../../../HttpServer/include/http/HttpServer.h"

using namespace http;

ChatServer::ChatServer(int port,
                       const std::string &name,
                       muduo::net::TcpServer::Option option)
    : httpServer_(port, name, option)
{
    initialize();
}

void ChatServer::initialize()
{
    std::cout << "ChatServer initialize start  ! " << std::endl;
    http::MysqlUtil::init("tcp://127.0.0.1:3306", "root", "Wyy13711570023!", "ChatHttpServer", 5);

    initializeSession();

    initializeMiddleware();

    initializeRouter();

    // 初始化leetcode表格
    // Initialize Leetcode Table
    std::string sql = "CREATE TABLE IF NOT EXISTS `study_records` ("
                      "`id` bigint(20) NOT NULL AUTO_INCREMENT,"
                      "`user_id` bigint(20) NOT NULL,"
                      "`problem_id` int(11) NOT NULL,"
                      "`problem_title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,"
                      "`difficulty` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,"
                      "`description` TEXT COLLATE utf8mb4_unicode_ci,"
                      "`test_cases` TEXT COLLATE utf8mb4_unicode_ci,"
                      "`stage` int(11) NOT NULL DEFAULT '0',"
                      "`last_review_time` bigint(20) NOT NULL DEFAULT '0',"
                      "`next_review_time` bigint(20) NOT NULL DEFAULT '0',"
                      "`status` int(11) NOT NULL DEFAULT '0',"
                      "PRIMARY KEY (`id`),"
                      "KEY `idx_user_next_review` (`user_id`,`next_review_time`)"
                      ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;";
    try
    {
        std::cout << "Starting table creation sequence..." << std::endl;

        std::cout << "Executing CREATE TABLE statement..." << std::endl;
        mysqlUtil_.executeUpdate(sql);
        std::cout << "CREATE TABLE finished." << std::endl;

        // Auto-migration
        std::cout << "Checking/Adding description column..." << std::endl;
        try
        {
            mysqlUtil_.executeUpdate("ALTER TABLE study_records ADD COLUMN description TEXT COLLATE utf8mb4_unicode_ci");
        }
        catch (const std::exception &e)
        {
            std::cout << "Alter 1 ignored: " << e.what() << std::endl;
        }

        std::cout << "Checking/Adding test_cases column..." << std::endl;
        try
        {
            mysqlUtil_.executeUpdate("ALTER TABLE study_records ADD COLUMN test_cases TEXT COLLATE utf8mb4_unicode_ci");
        }
        catch (const std::exception &e)
        {
            std::cout << "Alter 2 ignored: " << e.what() << std::endl;
        }

        std::cout << "Checking/Adding tutor_chat_history column..." << std::endl;
        try
        {
            mysqlUtil_.executeUpdate("ALTER TABLE study_records ADD COLUMN tutor_chat_history TEXT COLLATE utf8mb4_unicode_ci");
        }
        catch (const std::exception &e)
        {
            std::cout << "Alter 3 ignored: " << e.what() << std::endl;
        }

        std::cout << "Leetcode table init done" << std::endl;
    }
    catch (const std::exception &e)
    {
        LOG_ERROR << "Failed to init leetcode table: " << e.what();
    }
    catch (...)
    {
        LOG_ERROR << "Failed to init leetcode table: Unknown error";
    }
}

void ChatServer::initChatMessage()
{

    std::cout << "initChatMessage start ! " << std::endl;
    readDataFromMySQL();
    std::cout << "initChatMessage success ! " << std::endl;
}

void ChatServer::readDataFromMySQL()
{

    std::string sql = "SELECT id, username,session_id, is_user, content, ts FROM chat_message ORDER BY ts ASC, id ASC";

    sql::ResultSet *res;
    try
    {
        res = mysqlUtil_.executeQuery(sql);
    }
    catch (const std::exception &e)
    {
        std::cerr << "MySQL query failed: " << e.what() << std::endl;
        return;
    }

    while (res->next())
    {
        long long user_id = 0;
        std::string session_id;
        std::string username, content;
        long long ts = 0;
        int is_user = 1;

        try
        {
            user_id = res->getInt64("id");
            session_id = res->getString("session_id");
            username = res->getString("username");
            content = res->getString("content");
            ts = res->getInt64("ts");
            is_user = res->getInt("is_user");
        }
        catch (const std::exception &e)
        {
            std::cerr << "Failed to read row: " << e.what() << std::endl;
            continue;
        }

        auto &userSessions = chatInformation[user_id];

        std::shared_ptr<AIHelper> helper;
        auto itSession = userSessions.find(session_id);
        if (itSession == userSessions.end())
        {
            helper = std::make_shared<AIHelper>();
            userSessions[session_id] = helper;
            sessionsIdsMap[user_id].push_back(session_id);
        }
        else
        {
            helper = itSession->second;
        }

        helper->restoreMessage(content, ts);
    }

    std::cout << "readDataFromMySQL finished" << std::endl;
}

void ChatServer::setThreadNum(int numThreads)
{
    httpServer_.setThreadNum(numThreads);
}

void ChatServer::start()
{
    httpServer_.start();
}

void ChatServer::initializeRouter()
{

    httpServer_.Get("/", std::make_shared<ChatEntryHandler>(this));
    httpServer_.Get("/entry", std::make_shared<ChatEntryHandler>(this));

    httpServer_.Post("/login", std::make_shared<ChatLoginHandler>(this));

    httpServer_.Post("/register", std::make_shared<ChatRegisterHandler>(this));

    httpServer_.Post("/user/logout", std::make_shared<ChatLogoutHandler>(this));

    httpServer_.Get("/chat", std::make_shared<ChatHandler>(this));

    httpServer_.Post("/chat/send", std::make_shared<ChatSendHandler>(this));

    httpServer_.Get("/menu", std::make_shared<AIMenuHandler>(this));

    httpServer_.Get("/upload", std::make_shared<AIUploadHandler>(this));

    httpServer_.Post("/upload/send", std::make_shared<AIUploadSendHandler>(this));

    httpServer_.Post("/chat/history", std::make_shared<ChatHistoryHandler>(this));

    httpServer_.Post("/chat/send-new-session", std::make_shared<ChatCreateAndSendHandler>(this));
    httpServer_.Get("/chat/sessions", std::make_shared<ChatSessionsHandler>(this));

    httpServer_.Post("/chat/tts", std::make_shared<ChatSpeechHandler>(this));

    // Leetcode Handlers
    httpServer_.Get("/leetcode", std::make_shared<LeetcodePageHandler>(this));
    httpServer_.Post("/leetcode/daily", std::make_shared<LeetcodeDailyHandler>(this, mysqlUtil_)); // Changed to POST for userId
    httpServer_.Post("/leetcode/record", std::make_shared<LeetcodeRecordHandler>(this, mysqlUtil_));
    httpServer_.Post("/leetcode/analyze", std::make_shared<LeetcodeAnalyzeHandler>(this));
    httpServer_.Post("/leetcode/fetch", std::make_shared<LeetcodeProblemHandler>(this));

    // Agent Handlers
    httpServer_.Post("/leetcode/sandbox", std::make_shared<LeetcodeSandboxHandler>(this));
    httpServer_.Post("/leetcode/tutor", std::make_shared<LeetcodeTutorHandler>(this));

    // Tutor History
    httpServer_.Post("/leetcode/tutor/history/save", std::make_shared<LeetcodeTutorHistorySaveHandler>(this, mysqlUtil_));
    httpServer_.Post("/leetcode/tutor/history/get", std::make_shared<LeetcodeTutorHistoryGetHandler>(this, mysqlUtil_));
}

void ChatServer::initializeSession()
{

    auto sessionStorage = std::make_unique<http::session::MemorySessionStorage>();

    auto sessionManager = std::make_unique<http::session::SessionManager>(std::move(sessionStorage));

    setSessionManager(std::move(sessionManager));
}

void ChatServer::initializeMiddleware()
{

    auto corsMiddleware = std::make_shared<http::middleware::CorsMiddleware>();

    httpServer_.addMiddleware(corsMiddleware);
}

void ChatServer::packageResp(const std::string &version,
                             http::HttpResponse::HttpStatusCode statusCode,
                             const std::string &statusMsg,
                             bool close,
                             const std::string &contentType,
                             int contentLen,
                             const std::string &body,
                             http::HttpResponse *resp)
{
    if (resp == nullptr)
    {
        LOG_ERROR << "Response pointer is null";
        return;
    }

    try
    {
        resp->setVersion(version);
        resp->setStatusCode(statusCode);
        resp->setStatusMessage(statusMsg);
        resp->setCloseConnection(close);
        resp->setContentType(contentType);
        resp->setContentLength(contentLen);
        resp->setBody(body);

        LOG_INFO << "Response packaged successfully";
    }
    catch (const std::exception &e)
    {
        LOG_ERROR << "Error in packageResp: " << e.what();

        resp->setStatusCode(http::HttpResponse::k500InternalServerError);
        resp->setStatusMessage("Internal Server Error");
        resp->setCloseConnection(true);
    }
}
