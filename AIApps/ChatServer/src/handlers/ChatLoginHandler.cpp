#include "../include/handlers/ChatLoginHandler.h"

void ChatLoginHandler::handle(const http::HttpRequest &req, http::HttpResponse *resp)
{

    auto contentType = req.getHeader("Content-Type");
    if (contentType.empty() || contentType != "application/json" || req.getBody().empty())
    {
        LOG_INFO << "content" << req.getBody();
        resp->setStatusLine(req.getVersion(), http::HttpResponse::k400BadRequest, "Bad Request");
        resp->setCloseConnection(true);
        resp->setContentType("application/json");
        resp->setContentLength(0);
        resp->setBody("");
        return;
    }

    try
    {
        json parsed = json::parse(req.getBody());
        std::string username = parsed["username"];
        std::string password = parsed["password"];

        int userId = queryUserId(username, password);
        if (userId != -1)
        {
            auto session = server_->getSessionManager()->getSession(req, resp);

            {
                std::lock_guard<std::mutex> lock(server_->mutexForOnlineUsers_);
                auto it = server_->userSessionMap_.find(userId);
                if (it != server_->userSessionMap_.end())
                {
                    // 销毁旧 session
                    server_->getSessionManager()->destroySession(it->second);
                }
                // 记录新 session ID
                server_->userSessionMap_[userId] = session->getId();
                server_->onlineUsers_[userId] = true;
            }

            session->setValue("userId", std::to_string(userId));
            session->setValue("username", username);
            session->setValue("isLoggedIn", "true");

            // ✅ MODIFIED: 原来的逻辑是"发现用户已在 onlineUsers_ 里就返回403"，
            // 导致用户关掉浏览器（没点退出）后，onlineUsers_ 里的记录无法被清除，
            // 下次打开浏览器就永远进不去了。
            //
            // 修改策略：放弃单点登录限制，改为"重新登录直接覆盖旧状态"。
            // 如需单点登录，应改用带 TTL 的 Session 超时机制，而不是内存 bool 标记。
            {
                std::lock_guard<std::mutex> lock(server_->mutexForOnlineUsers_);
                server_->onlineUsers_[userId] = true; // 直接覆盖，无论之前是否在线
            }

            json successResp;
            successResp["success"] = true;
            successResp["userId"] = userId;
            std::string successBody = successResp.dump(4);

            resp->setStatusLine(req.getVersion(), http::HttpResponse::k200Ok, "OK");
            resp->setCloseConnection(false);
            resp->setContentType("application/json");
            resp->setContentLength(successBody.size());
            resp->setBody(successBody);
            return;

            // ❌ REMOVED: 以下 else 分支已被删除，不再因为"已在线"而返回 403 Forbidden
            // else
            // {
            //     json failureResp;
            //     failureResp["success"] = false;
            //     failureResp["error"] = "已在别处登录";
            //     std::string failureBody = failureResp.dump(4);
            //
            //     resp->setStatusLine(req.getVersion(), http::HttpResponse::k403Forbidden, "Forbidden");
            //     resp->setCloseConnection(true);
            //     resp->setContentType("application/json");
            //     resp->setContentLength(failureBody.size());
            //     resp->setBody(failureBody);
            //     return;
            // }
        }
        else
        {
            json failureResp;
            failureResp["status"] = "error";
            failureResp["message"] = "Invalid username or password";
            std::string failureBody = failureResp.dump(4);

            resp->setStatusLine(req.getVersion(), http::HttpResponse::k401Unauthorized, "Unauthorized");
            resp->setCloseConnection(false);
            resp->setContentType("application/json");
            resp->setContentLength(failureBody.size());
            resp->setBody(failureBody);
            return;
        }
    }
    catch (const std::exception &e)
    {
        json failureResp;
        failureResp["status"] = "error";
        failureResp["message"] = e.what();
        std::string failureBody = failureResp.dump(4);

        resp->setStatusLine(req.getVersion(), http::HttpResponse::k400BadRequest, "Bad Request");
        resp->setCloseConnection(true);
        resp->setContentType("application/json");
        resp->setContentLength(failureBody.size());
        resp->setBody(failureBody);
        return;
    }
}

int ChatLoginHandler::queryUserId(const std::string &username, const std::string &password)
{
    std::string sql = "SELECT id FROM users WHERE username = ? AND password = ?";
    auto res = mysqlUtil_.executeQuery(sql, username, password);
    if (res->next())
    {
        int id = res->getInt("id");
        return id;
    }

    return -1;
}
