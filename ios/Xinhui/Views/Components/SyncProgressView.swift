import SwiftUI

struct SyncProgressView: View {
    let progress: SyncProgress

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ProgressView(value: progress.fractionCompleted)
                .tint(tintColor)

            HStack {
                if let current = progress.currentType {
                    Image(systemName: current.iconName)
                        .foregroundColor(.accentColor)
                    Text(statusText(for: current))
                        .font(.caption)
                        .foregroundColor(.secondary)
                } else {
                    Text(progress.phase.rawValue)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                Spacer()
                Text("\(Int(progress.fractionCompleted * 100))%")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(Constants.cornerRadius)
        .cardBorder()
    }

    private var tintColor: Color {
        switch progress.phase {
        case .done: return .green
        case .failed: return .red
        default: return .accentColor
        }
    }

    private func statusText(for type: HealthDataType) -> String {
        switch progress.phase {
        case .querying: return "正在读取\(type.rawValue)..."
        case .uploading: return "正在上传数据..."
        default: return type.rawValue
        }
    }
}
