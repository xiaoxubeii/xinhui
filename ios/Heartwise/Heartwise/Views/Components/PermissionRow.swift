import SwiftUI

struct PermissionRow: View {
    let name: String
    let granted: Bool

    var body: some View {
        HStack {
            Text(name)
            Spacer()
            Image(systemName: granted ? "checkmark.circle.fill" : "xmark.circle")
                .foregroundColor(granted ? .green : .red)
        }
    }
}
