import Foundation
import AVFoundation

public class IOSAudioEngine: ObservableObject {
    private let audioEngine = AVAudioEngine()
    @Published public var isMuted: Bool = false
    @Published public var audioLevelDb: Float = -60.0

    public init() {}

    public func start() {
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(.playAndRecord, mode: .videoRecording, options: [.defaultToSpeaker, .allowBluetooth])
            try session.setActive(true)

            let inputNode = audioEngine.inputNode
            let recordingFormat = inputNode.outputFormat(forBus: 0)

            inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { [weak self] (buffer, _) in
                guard let self = self, !self.isMuted else {
                    DispatchQueue.main.async { self?.audioLevelDb = -60.0 }
                    return
                }

                guard let channelData = buffer.floatChannelData?[0] else { return }
                let channelDataValue = Array(UnsafeBufferPointer(start: channelData, count: Int(buffer.frameLength)))

                var sum: Float = 0
                for sample in channelDataValue {
                    sum += sample * sample
                }
                let rms = sqrt(sum / Float(buffer.frameLength))
                let db = rms > 0 ? 20 * log10(rms) : -60.0

                DispatchQueue.main.async {
                    self.audioLevelDb = max(-60.0, min(0.0, db))
                }
            }

            try audioEngine.start()
        } catch {
            print("Audio engine failed to start: \(error)")
        }
    }

    public func stop() {
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        audioLevelDb = -60.0
    }
}

