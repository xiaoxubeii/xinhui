import SwiftUI

struct PlanProgressRow: View {
    let item: PlanProgressItem

    private var valueText: String {
        String(format: "%.0f / %.0f %@", item.current, item.target, item.unit)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(item.title)
                    .font(.caption)
                    .foregroundColor(.secondary)
                Spacer()
                Text(valueText)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            ProgressView(value: item.progress)
        }
    }
}
