import Foundation
import UIKit

enum ImageEncoding {
    static func jpegBase64(
        from image: UIImage,
        maxDimension: CGFloat = 1024,
        compressionQuality: CGFloat = 0.7
    ) -> String? {
        let resized = resize(image: image, maxDimension: maxDimension)
        guard let data = resized.jpegData(compressionQuality: compressionQuality) else { return nil }
        return data.base64EncodedString()
    }

    private static func resize(image: UIImage, maxDimension: CGFloat) -> UIImage {
        let width = image.size.width
        let height = image.size.height
        guard width > 0, height > 0 else { return image }

        let maxSide = max(width, height)
        guard maxSide > maxDimension else { return image }

        let scale = maxDimension / maxSide
        let newSize = CGSize(width: width * scale, height: height * scale)

        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        let renderer = UIGraphicsImageRenderer(size: newSize, format: format)
        return renderer.image { _ in
            image.draw(in: CGRect(origin: .zero, size: newSize))
        }
    }
}

