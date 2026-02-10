import SwiftUI

extension View {
    func cardBorder() -> some View {
        overlay(
            RoundedRectangle(cornerRadius: Constants.cornerRadius)
                .stroke(Color(.separator).opacity(0.4), lineWidth: 1)
        )
    }
}
