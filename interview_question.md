# AI题目评测与学习计划系统 - 面试题库及话术 (大厂校招/秋招深挖)

经过对项目代码（Muduo网络底层、HttpServer解析、MySQL连接池、RabbitMQ及业务算法）的梳理，**你简历中的项目描述非常扎实且逻辑自洽，完全可以这样写。** 简历中突出了 Reactor 模型、非阻塞 I/O、连接池、异步削峰等高频考点。

以下为你准备的不少于15道大厂深挖面试题。回答均采用**“总分总”**结构，并明确标注了对应的代码文件。

---

### 1. 为什么选择基于 Muduo 网络库来构建基础服务端？相比直接用 Spring 这种成熟框架有什么思考？
**【回答话术】**
我选择 Muduo 主要出于对底层网络机制的深度掌控力以及 C++ 极致性能的考量。
第一，Muduo 采用了基于 Epoll 的 One Loop Per Thread 的 Reactor 模型，针对网络 I/O 密集型的场景有着极佳的并发处理能力；
第二，相比直接使用 Spring Boot 等高度封装的框架，基于 Muduo 让我能够亲自从底层去实现 HTTP 协议的拆包解析以及动态路由分发，这极大地加深了我对网络协议和事件驱动模型的理解；
第三，C++ 能够提供更加精细的内存控制，在面对极高频的并发长连接时，能够压榨单机的极限性能。
总结来说，基于 Muduo 搭建服务端既保证了项目对高并发大吞吐的要求，又是一次深入底层原理的极佳实践。
**【涉及文件】**
- `HttpServer/include/http/HttpServer.h`
- `HttpServer/src/http/HttpServer.cpp`

---

### 2. 请详细说一下你的 HttpContext 是如何独立实现 HTTP 协议解析的？遇到了什么问题？
**【回答话术】**
我的 HttpContext 主要是通过一种有限状态机（FSM）的机制来完成 HTTP 报文的非阻塞解析的。
第一，在接收到 Muduo 传来的 Buffer 后，我定义了三个解析状态：解析请求行（kExpectRequestLine）、解析请求头（kExpectHeaders）和解析请求体（kExpectBody）。
第二，我通过寻找回车换行符 `\r\n` (CRLF) 来逐行读取数据。在解析请求头时，会特别提取 `Content-Length`，以此来判断请求体的大小并在下个状态中精确截取 Body 数据；
第三，在实现过程中遇到过 TCP 粘包和半包的问题。由于是非阻塞 I/O，数据可能一次读不完。状态机完美解决了这个问题，如果 Buffer 数据不够（比如小于 Content-Length），状态机会挂起并返回 `true` 等待下一次 Epoll 可读事件触发继续解析，不会阻塞主线程。
总体而言，通过引入状态机，我将复杂的流式数据解析变得结构化和安全，保证了高并发下的解析正确性。
**【涉及文件】**
- `HttpServer/include/http/HttpContext.h`
- `HttpServer/src/http/HttpContext.cpp`
- `HttpServer/src/http/HttpRequest.cpp`

---

### 3. 项目里提到了“动态路由分发 (Dispatcher)”，能具体讲讲你的路由层是怎么设计和解耦的吗？
**【回答话术】**
我的动态路由层主要是通过注册回调函数的方式，将底层网络解析和上层业务逻辑进行彻底解耦的。
第一，在 Router 类中，我底层维护了哈希表结构，将 HTTP Method 和 URL Path 作为键，将对应的业务处理函数（Handler）或闭包作为值来进行映射；
第二，当 HttpContext 完成报文解析后，服务器会根据 Request 的 Method 和 URL，在 Router 中以 O(1) 的时间复杂度查找命中的 Handler，并将请求交由其处理；
第三，这种设计使得未来添加新接口（例如增加一个`/leetcode/record`）时，只需要在 server 初始化时 `Post(...)` 注册对应的 Handler 即可，无需修改底层网络或解析层的核心代码。
总结来看，这种类似于策略模式的路由分发机制，让网络通信层和业务逻辑层实现了完全分离，极大提升了代码的可维护性和扩展性。
**【涉及文件】**
- `HttpServer/include/router/Router.h`
- `HttpServer/src/http/HttpServer.cpp`

---

### 4. 简历中写道“封装 MySQL 连接池控制查询在毫秒级”，连接池具体解决了什么问题？
**【回答话术】**
引入 MySQL 连接池本质上是为了消除频繁的 TCP 握手开销以及数据库鉴权带来的延迟，从而实现毫秒级查询。
第一，在传统的短连接模式下，每次数据库操作都需要经历 TCP 三次握手、MySQL 账号密码校验、断开时的四次挥手，这个网络消耗对于毫秒级的接口是不可接受的；
第二，我通过 `DbConnectionPool` 在服务启动时预先初始化了一组与 MySQL 的长连接，并存放在队列中。当有业务请求到来时，直接从池中获取可用连接，用完后再归还；
第三，我还加入了基于互斥锁和条件变量的线程安全队列机制，如果连接池被用尽，新请求会阻塞等待直到有空闲连接被释放。
总的来说，连接池化技术是典型的空间换时间策略，有效平滑了数据库的连接压力，保障了上层 API 的极速响应。
**【涉及文件】**
- `HttpServer/include/utils/db/DbConnectionPool.h`
- `HttpServer/src/utils/db/DbConnectionPool.cpp`

---

### 5. 你的 MySQL 毫秒级检索，在千万级数据或者高并发下，你是怎么做结构化存储优化的？
**【回答话术】**
针对海量做题记录的单表检索，我在表结构和索引设计上进行了针对性的优化。
第一，我在建表时针对高频查询的核心字段建立了联合索引。例如刷题记录表中的 `user_id` 和 `next_review_time`。因为业务中最常见的操作就是“查询某用户今天要复习的题目”；
第二，利用联合索引树的特性，原先需要全表扫描的查询 `WHERE user_id = X AND next_review_time <= Y`，现在可以直接走到命中索引并利用最左前缀法则过滤，避免了回表查询带来的额外 I/O 开销；
第三，我将不需要参与检索的题目具体描述和大段代码等字段，存储为 TEXT 类型，防止页分裂和 B+ 树层级过深。
综上，这种基于业务查询模式定制的联合索引，确保了即便单表数据量不断膨胀，我的分页拉取和检索时长也能稳定在毫秒级。
**【涉及文件】**
- `AIApps/ChatServer/resource/init_leetcode.sql`
- `AIApps/ChatServer/src/ChatServer.cpp`

---

### 6. 为什么会在 AI 会话日志落库这个场景引入 RabbitMQ？它起到了什么作用？
**【回答话术】**
引入 RabbitMQ 最大的意义在于实现异步写入（写后即忘）和主线程流量削峰。
第一，用户与 AI 的交互往往会产生长篇的文本（如代码分析、解题思路），如果直接在 HTTP 业务线程同步等待写 MySQL 成功返回，会大幅增加单次请求的响应耗时，降低用户体验；
第二，通过引入 RabbitMQ，当业务侧拿到 AI 返回的文本时，只需将需要落库的历史日志作为一条 Message 推送到消息队列中即可立刻向前端返回结果；
第三，我在后端另外启动了独立的 `RabbitMQThreadPool` 消费者线程，慢慢从队列中取出消息再写入 MySQL。即使流量突发，积压的也只是 MQ 中的消息，保护了 MySQL 不被瞬时高并发打挂。
总体来看，在这个非强一致性要求的日志场景中引人 MQ，完美做到了网络主线程不受阻塞和数据库的削峰填谷。
**【涉及文件】**
- `AIApps/ChatServer/include/AIUtil/MQManager.h`
- `AIApps/ChatServer/src/main.cpp`
- `AIApps/ChatServer/src/AIUtil/AIHelper.cpp`

---

### 7. 对话系统是如何精准管理上下文的？你简历里提到的双层 Map 是怎么运作的？
**【回答话术】**
为了突破传统系统单用户单会话的瓶颈，我设计了一套细粒度的并发上下文管理结构。
第一，由于用户可能同时在网页端开多个窗口与不同的题目进行 AI 提问，我采用 `unordered_map<userId, map<sessionId, AIHelper>>` 的结构。外层通过 `userId` 隔离不同用户，内层通过 `sessionId` 隔离同一个用户不同题目的会话；
第二，每个 `sessionId` 都会绑定一个 `AIHelper` 实例，该实例内部维护了和 AI 对话的上下文列表（History messages）。这意味着不同对话的上下文完全物理隔离，不会发生逻辑串扰；
第三，为了防止数据竞态，在通过 `userId` 和 `sessionId` 寻找对应 `AIHelper` 时，由于 C++ 标准库中的 Map 不是线程安全的，我在这层操作上引入了读写锁（或互斥锁），确保在创建或删除会话时线程安全。
总的来说，细粒度的状态维护确保了大模型能够准确关联每次会话的历史文脉，带来连贯的 AI 问答体验。
**【涉及文件】**
- `HttpServer/include/session/SessionManager.h`
- `AIApps/ChatServer/src/AIUtil/AIHelper.cpp`

---

### 8. 这个项目中的“艾宾浩斯记忆曲线算法”具体在代码里是怎么落地的？
**【回答话术】**
在项目中，艾宾浩斯记忆曲线并不是一个复杂的数学公式，而是被我落地为一套基于“学习阶段（Stage）”跳跃的离散时间计算模型。
第一，我在数据库 `study_records` 表中维护了两个核心字段：`stage`（掌握阶段）和 `next_review_time`（下次复习时间戮）；
第二，当用户提交复习反馈后，服务端的 `LeetcodeRecordHandler::calculateNextReview` 函数会介入。如果用户点击了“掌握”或完成了本次复习，`stage` 会递增。根据当前的 `stage` 值，利用 switch 匹配，推算出分别对应 1天、2天、4天、7天、15天、30天后的时间戳，并存入 `next_review_time`；
第三，如果用户点击了“遗忘”，则 `stage` 归零，强制其第二天再次复习。日常的获取复习任务接口只需查询 `next_review_time <= now()` 的记录即可。
总结来说，我将复杂的心理学曲线降维成了一套简洁高效的状态机转移逻辑，配合时间戳比对，非常轻量且完美满足了业务需求。
**【涉及文件】**
- `AIApps/ChatServer/src/handlers/LeetcodeHandler.cpp`

---

### 9. 简历里写到“自研的轻量级自动表结构迁移（Auto-Migration）”，它是怎么工作的？
**【回答话术】**
这是针对 C++ 服务端在不引入笨重 ORM 框架时，解决表结构升级迭代痛点的一个轻量级手段。
第一，我在项目升级过程中，经常需要为某张表增加字段（例如新增 `description` 描述或 `test_cases`）。传统的做法是手动执行 SQL，很容易导致不同环境同步遗漏部署；
第二，在我的系统启动初始化方法（`ChatServer`构造函数）中，程序会尝试执行硬编码的 `ALTER TABLE ADD COLUMN` 语句；
第三，为了防止字段已存在导致的宕机，我利用了 C++ 的 `try-catch` 异常捕获机制。若 MySQL 抛出“列已存在”的异常，程序会捕获该异常仅打印普通 log，然后继续往下执行。
综上，这种做法虽然原始但极其轻量有效。它随 C++ 程序一键运行，保证了开发环境和生产环境启动时数据库结构的天然一致性。
**【涉及文件】**
- `AIApps/ChatServer/src/ChatServer.cpp`

---

### 10. 在本项目开发中，你在防范 SQL 注入方面做了哪些工作？
**【回答话术】**
防范 SQL 注入是业务接口安全的基本功。我在项目中采用了预编译和自定义转义双管齐下的方式。
第一，在使用 MySQL-Connector-C++ 时，核心的查询和写入操作（如用户登录鉴权），我尽可能优先使用原生的预编译功能。底层驱动会自动帮我们规避恶意语法的拼接；
第二，对于大量需要动态拼接的复杂 SQL，我实现了一个自定义的 `escapeSQL` Lambda 函数，它会对传入字符串中敏感的单引号、双引号、反斜杠等字符进行安全的转义（比如将 `'` 变成 `\'`）；
第三，我在处理所有 JSON 反序列化的入参时也加强了类型校验。
通过对请求参数全方位的特殊字符清理，杜绝了带有截断含义或恶意 `DROP TABLE` 等 SQL 片段被作为指令执行。
**【涉及文件】**
- `AIApps/ChatServer/src/handlers/LeetcodeHandler.cpp`

---

### 11. 目前大模型层出不穷，你的平台是如何做到方便地接入和切换多个大模型引擎（如阿里云、豆包、DeepSeek等）的？
**【回答话术】**
为了解决多模型适配的问题，我在代码设计中引入了典型的“策略模式（Strategy Pattern）”。
第一，我定义了一个抽象基类 `AIStrategy`，其中抽出了模型请求和响应所需的纯虚函数，如 `buildRequest()` 用于封装数据结构，`parseResponse()` 用于解析返回的非标准 JSON；
第二，针对阿里云百炼、字节豆包、DeepSeek、OpenAI 等不同服务商，我分别实现了独立的派生类。每个平台可能需要的认证头、JSON 结构体层级各不相同，这些差异化处理都封闭在各自独立的子类中；
第三，在业务的 `AIHelper` 模块层，只需持有一个 `AIStrategy` 的基类指针。当需要切换模型时，只需通过工厂模式改变这个指针的实例即可，上层业务代码无需任何改动。
总而言之，策略模式彻底隔离了第三方 API 多变的数据结构，完美满足了开闭原则（对扩展开放，对修改封闭）。
**【涉及文件】**
- `AIApps/ChatServer/include/AIUtil/AIStrategy.h`
- `AIApps/ChatServer/src/AIUtil/AIStrategy.cpp`

---

### 12. 代码提交给 AI 进行判题分析后，返回的可能是带有 Markdown 格式的一长串文本，你是怎么把它变成可靠的结构化 JSON 返回给前端的？
**【回答话术】**
处理大模型输出的非结构化脏数据是 AI 应用开发中非常典型的顽疾，我通过 Prompt 工程和正则清洗两步走来解决。
第一，在构造请求时（Prompt），我通过强烈的指令词要求大模型：“请确保返回的是纯 JSON 字符串，不要包含任何 markdown 代码块标记”；
第二，即便如此，模型依旧偶尔会自作聪明地加上 ````json ` 和 ` ```` ` 的包裹。为此，我在 C++ 的 Handler 中引入了正则表达式 `<regex>` 组件。在拿到回答后，先行使用 `std::regex_replace` 剔除可能存在的 Markdown 代码块首尾标记；
第三，清洗完毕后才调用 `nlohmann::json::parse` 去反序列化。如果解析依然抛出异常，我会在 catch 块中进行兜底，返回友好的错误体，防止服务器挂掉。
这种服务端清洗机制使得前端拿到的永远是合法的 JSON 对象，保证了网页渲染不出错。
**【涉及文件】**
- `AIApps/ChatServer/src/handlers/LeetcodeHandler.cpp` (LeetcodeProblemHandler及LeetcodeAnalyzeHandler)

---

### 13. 你在项目中提到了 Reactor 模型，那请问 Muduo 中 EventLoop 的核心机制是什么？
**【回答话术】**
Muduo 的 EventLoop 是整个 Reactor 模型的心脏，本质是一个无限循环的事件分发器。
第一，它的核心是一个 `while(!quit_)` 的循环。在循环内部，它会调用底层的 I/O 多路复用器（通常是 Epoll 的 `epoll_wait`），阻塞等待注册在它上面的文件描述符发生就绪事件；
第二，当事件到来时，Epoll 返回活跃的 Channel 列表，EventLoop 会逐个调用这些 Channel 预先绑定的回调函数，比如处理读数据的 `handleRead` 或者处理新连接的 `handleConn`；
第三，除了处理 I/O 事件，EventLoop 还兼顾了任务队列（Pending Functors）的消费，以及定时器任务的处理。以此保证一个线程既能处理 I/O 也能异步执行计算逻辑。
总的来说，EventLoop 将所有的异步事件转变成了串行且线程安全的回调执行，是 One Loop Per Thread 思想的最佳诠释。
**【涉及文件】**
- `HttpServer/include/http/HttpServer.h` (底层的Muduo架构)

---

### 14. 为什么在这个项目中，Muduo 底层使用了 Epoll 而不是 Select 或者是 Poll？
**【回答话术】**
这是从时间复杂度和内核机制上决定的，主要由于 Epoll 针对高并发长连接有着压倒性的优势。
第一，Select 和 Poll 底层都是基于轮询（O(N)）的方式，当有大量连接（几万个）但只有少数几个活跃时，它们依然要遍历整个文件描述符集合，且具有最大文件描述符的限制（Select 默认1024）；
第二，Epoll 采用了事件通知机制（O(1)算法复杂度）。内核会把就绪的描述符主动添加到一个准备就绪的双向链表中。`epoll_wait` 只需要去这个链表里拿数据就行，连接数再多也不会引起性能骤降；
第三，Epoll 使用了 `mmap` 内存映射技术，省去了用户态和内核态之间频繁拷贝文件描述符集合带来的系统开销。
总结来说，面对基于 HTTP 抓取的爬虫以及 AI 聊天这种长期保持连接不变的上下文场景，利用 Epoll 能以最少的资源榨取最高的并发性能。
**【涉及文件】**
- `HttpServer/src/http/HttpServer.cpp` (Muduo底层封装)

---

### 15. 最后，简历上写了将后端封装成了 v1/v2 Docker 镜像部署。为什么要这么做？
**【回答话术】**
容器化部署是我在解决环境不一致和项目运维成本过高时引入的手段。
第一，在没有容器化之前，在不同服务器上拉起这个 C++ 后端，需要重新编译各种第三方库（如 MySQL Connector、RabbitMQ-c、Nlohmann-json），往往会遇到动态链接库（.so）找不到的噩梦；
第二，通过编写 Dockerfile，我将 C++ 的编译环境、运行期依赖全部固化到了镜像体内。另外结合 docker-compose，我可以一键式把 MySQL 数据库、RabbitMQ 服务端以及我的应用服务一并声明式启动；
第三，这极大简化了项目的交付流程。只需对外打包发布一个镜像版本标签，任何人拉取都能实现“开箱即用”。
综合来看，Docker 真正打通了项目从本地开发流向生成交付的最后一公里，是现代化微服务开发必备的能力。
**【涉及文件】**
- `README.md` (项目环境搭建指南与架构设计)
