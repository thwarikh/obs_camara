import Foundation

public protocol SignalingWebSocketDelegate: AnyObject {
    fun onConnected()
    fun onDisconnected()
    fun onCommandReceived(command: [String: Any])
}

public class SignalingWebSocket {
    private var webSocketTask: URLSessionWebSocketTask?
    private let urlSession = URLSession(configuration: .default)
    public weak var delegate: SignalingWebSocketDelegate?

    public init() {}

    public func connect(host: String, port: Int, deviceId: String) {
        guard let url = URL(string: "ws://\(host):\(port)/ws/camera/\(deviceId)") else { return }
        webSocketTask = urlSession.webSocketTask(with: url)
        webSocketTask?.resume()
        receiveMessage()
        delegate?.onConnected()
    }

    private func receiveMessage() {
        webSocketTask?.receive { [weak self] result in
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    if let data = text.data(using: .utf8),
                       let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                        self?.delegate?.onCommandReceived(command: json)
                    }
                default: break
                }
                self?.receiveMessage()
            case .failure:
                self?.delegate?.onDisconnected()
            }
        }
    }

    public func sendTelemetry(fps: Float, bitrateKbps: Int, batteryPct: Int, audioLevelDb: Float) {
        let payload: [String: Any] = [
            "type": "telemetry",
            "payload": [
                "fps": fps,
                "bitrate_kbps": bitrateKbps,
                "battery_pct": batteryPct,
                "audio_level_db": audioLevelDb,
                "network_type": "wifi"
            ]
        ]
        if let data = try? JSONSerialization.data(withJSONObject: payload),
           let str = String(data: data, encoding: .utf8) {
            webSocketTask?.send(.string(str)) { _ in }
        }
    }

    public func disconnect() {
        webSocketTask?.cancel(with: .normalClosure, reason: nil)
    }
}

