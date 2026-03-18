#pragma once

#include <atomic>
#include <memory>
#include <tuple>
#include <unordered_map>
#include <mutex>
#include <cstdlib>
#include <ctime>
#include <iostream>
#include <string>
#include <vector>

#include "../../../HttpServer/include/http/HttpServer.h"
#include "../../../HttpServer/include/utils/MysqlUtil.h"
#include "../../../HttpServer/include/utils/FileUtil.h"
#include "../../../HttpServer/include/utils/JsonUtil.h"
#include "AIUtil/AISpeechProcessor.h"
#include "AIUtil/AIHelper.h"
#include "AIUtil/ImageRecognizer.h"
#include "AIUtil/base64.h"
#include "AIUtil/MQManager.h"

class ChatLoginHandler;	   // 负责处理用户登录请求 (校验账号密码，下发 Token/Session)
class ChatRegisterHandler; // 负责处理用户注册请求 (将新用户凭证插入 MySQL 数据库)
class ChatLogoutHandler;   // 负责处理用户注销请求 (清除在线状态和对应的 Session)
class ChatHandler;		   // 负责渲染/返回主聊天界面资源 (HTML 页面)
class ChatEntryHandler;	   // 负责返回程序的默认入口页面或网关路由
class ChatSendHandler;	   // 负责处理已有会话的各种发送请求 (调用底层 AIHelper 生成大模型回复并入库)
class ChatHistoryHandler;  // 负责拉取和下发历史对话记录 (用于前端页面刷新或切换会话时渲染列表)

class AIMenuHandler;	   // 负责获取 AI 系统菜单/控制面板页 (如侧边栏、模型设置面板)
class AIUploadHandler;	   // 负责渲染/处理图片上传界面的前端交互 (视觉多模态相关)
class AIUploadSendHandler; // 负责处理附带图片的聊天发送请求 (视觉大模型解析任务，对接 ImageRecognizer)

class ChatCreateAndSendHandler; // 负责核心的新建会话并首次发送消息逻辑 (分配 sessionId，初始化上下文本环境)
class ChatSessionsHandler;		// 负责管理获取用户的会话列表 (如获取该用户的所有会话 ID 和对应的首条预览标题)
class ChatSpeechHandler;		// 负责处理所有与语音相关的操作 (接收前端音频调用 ASR 转字，或者生成回复调用 TTS 返回音频)



class ChatServer
{
public:
	ChatServer(int port,
			   const std::string &name,
			   muduo::net::TcpServer::Option option = muduo::net::TcpServer::kNoReusePort);

	void setThreadNum(int numThreads);
	void start();
	void initChatMessage();

private:
	friend class ChatLoginHandler;
	friend class ChatRegisterHandler;
	friend ChatLogoutHandler;
	friend class ChatHandler;
	friend class ChatEntryHandler;
	friend class ChatSendHandler;
	friend class AIMenuHandler;
	friend class AIUploadHandler;
	friend class AIUploadSendHandler;
	friend class ChatHistoryHandler;

	friend class ChatCreateAndSendHandler;
	friend class ChatSessionsHandler;
	friend class ChatSpeechHandler;

private:
	void initialize();
	void initializeSession();
	void initializeRouter();
	void initializeMiddleware();

	void readDataFromMySQL();

public:
	// 这是一个帮助业务代码快速构造 200 OK 或者 404 等响应包的工具函数
	void packageResp(const std::string &version, http::HttpResponse::HttpStatusCode statusCode,
					 const std::string &statusMsg, bool close, const std::string &contentType,
					 int contentLen, const std::string &body, http::HttpResponse *resp);

private:
	void setSessionManager(std::unique_ptr<http::session::SessionManager> manager)
	{
		httpServer_.setSessionManager(std::move(manager));
	}
	http::session::SessionManager *getSessionManager() const
	{
		return httpServer_.getSessionManager();
	}

	http::HttpServer httpServer_;

	http::MysqlUtil mysqlUtil_;

	// 1. 在线状态表
	// 映射: UserID(整形) -> 是否在线(bool)
	std::unordered_map<int, bool> onlineUsers_;
	std::mutex mutexForOnlineUsers_; // 保护 onlineUsers_ 的锁

	// 2. 对话助手缓存表 (极重要：多租户+多会话实现点)
	// 映射: UserID -> { SessionID(字符串) -> AIHelper大模型助手实例 }
	// 第一版是一维的，第二版这里改成了二维 map，完美实现了单人在不同网页建立不同会话。
	std::unordered_map<int, std::unordered_map<std::string, std::shared_ptr<AIHelper>>> chatInformation;
	std::mutex mutexForChatInformation; // 保护 chatInformation 的锁

	// 3. 视觉识别助手表
	// 映射: UserID -> VLM视觉大模型组件
	std::unordered_map<int, std::shared_ptr<ImageRecognizer>> ImageRecognizerMap;
	std::mutex mutexForImageRecognizerMap; // 保护 ImageRecognizerMap 的锁

	// 4. 用户会话 ID 列表
	// 映射: UserID -> 他的所有会话 ID 数组
	// 用来渲染首页的“历史聊天列表”侧边栏
	std::unordered_map<int, std::vector<std::string>> sessionsIdsMap;
	std::mutex mutexForSessionsId; // 保护 sessionsIdsMap 的锁

	// HTTP 的 Session 对应表 (用来管理网页登录态 Token 的)
	std::unordered_map<int, std::string> userSessionMap_;
};
