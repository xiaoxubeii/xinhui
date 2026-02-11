import SwiftUI

struct PlanCard: View {
    let title: String
    let subtitle: String
    let iconName: String
    let color: Color
    var showsChevron: Bool = true

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: iconName)
                .font(.title3)
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
            if showsChevron {
                Image(systemName: "chevron.right")
                    .font(.footnote)
                    .foregroundColor(.secondary)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(Constants.cornerRadius)
        .cardBorder()
        .shadow(color: .black.opacity(0.04), radius: 2, y: 1)
    }
}
