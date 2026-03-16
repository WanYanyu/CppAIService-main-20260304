#pragma once

// amqp就是rabbitmq的协议库
#include <SimpleAmqpClient/SimpleAmqpClient.h>
#include <vector>
#include <mutex>
#include <memory>
#include <atomic>
#include <thread>
#include <iostream>
#include <chrono>
#include <functional>

// 高并发的“消息发送者” (Producer)
// 这个类的核心定位是一个带有连接池的单例生产者。它的职责是高效、线程安全地把消息推送到 RabbitMQ 中。
class MQManager {
public:
    static MQManager& instance() {
        static MQManager mgr;
        return mgr;
    }

    void publish(const std::string& queue, const std::string& msg);

private:
    // 定义信道
    struct MQConn {
        AmqpClient::Channel::ptr_t channel;
        std::mutex mtx;
    };
    
    MQManager(size_t poolSize = 5);

    MQManager(const MQManager&) = delete;
    MQManager& operator=(const MQManager&) = delete;

    // std::vector<std::shared_ptr<MQConn>> pool_ 维护了一个连接池（默认大小为 poolSize = 5）
    std::vector<std::shared_ptr<MQConn>> pool_;
    size_t poolSize_;
    std::atomic<size_t> counter_;
};


// 高并发的“消息接收者” (Consumer)
class RabbitMQThreadPool {
public:
    using HandlerFunc = std::function<void(const std::string&)>;

    RabbitMQThreadPool(const std::string& host,
        const std::string& queue,
        int thread_num,
        HandlerFunc handler)
        : stop_(false),
        rabbitmq_host_(host),
        queue_name_(queue),
        thread_num_(thread_num),
        handler_(handler) {}

    void start();
    void shutdown();

    ~RabbitMQThreadPool() {
        shutdown();
    }

private:
    void worker(int id);

private:
    std::vector<std::thread> workers_;
    std::atomic<bool> stop_;
    std::string queue_name_;
    int thread_num_;
    std::string rabbitmq_host_;
    HandlerFunc handler_;
};
