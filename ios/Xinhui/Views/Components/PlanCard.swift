import SwiftUI

struct PlanCard: View {
    let title: String
    let subtitle: String
    let iconName: String
    let color: Color

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: iconName)
                .foregroundColor(color)
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.headline)
                Text(subtitle)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(2)
            }
            Spacer()
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(Constants.cornerRadius)
        .shadow(color: .black.opacity(0.04), radius: 2, y: 1)
    }
}
