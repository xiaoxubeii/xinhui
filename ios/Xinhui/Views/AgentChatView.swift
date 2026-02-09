import SwiftUI
import PhotosUI
import UniformTypeIdentifiers
import UIKit

struct AgentChatView: View {
    @StateObject private var viewModel = AgentChatViewModel()
    @State private var includeContext = true
    @State private var contextExpanded = true
    @State private var photoItem: PhotosPickerItem?
    @State private var showFileImporter = false

    var body: some View {
        VStack(spacing: 0) {
            contextCard
                .padding(.horizontal)
                .padding(.top, 12)

            Divider()
                .padding(.top, 8)

            messagesView

            Divider()

            inputBar
                .padding(.horizontal)
                .padding(.vertical, 10)
                .background(Color(.systemBackground))
        }
        .background(Color(.systemGroupedBackground))
        .navigationTitle("智问")
        .navigationBarTitleDisplayMode(.inline)
        .task { await viewModel.loadContextIfNeeded() }
        .onChange(of: photoItem) { _, newValue in
            guard let newValue else { return }
            Task {
                await handlePhotoItem(newValue)
                photoItem = nil
            }
        }
        .fileImporter(
            isPresented: $showFileImporter,
            allowedContentTypes: [.item],
            allowsMultipleSelection: true
        ) { result in
            switch result {
            case .success(let urls):
                for url in urls {
                    Task { await viewModel.addFileAttachment(url: url) }
                }
            case .failure(let error):
                viewModel.attachmentError = "选择文件失败：\(error.localizedDescription)"
            }
        }
        .alert(
            "附件提示",
            isPresented: Binding(
                get: { viewModel.attachmentError != nil },
                set: { if !$0 { viewModel.attachmentError = nil } }
            )
        ) {
            Button("确定", role: .cancel) {}
        } message: {
            Text(viewModel.attachmentError ?? "未知错误")
        }
    }

    private var contextCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 10) {
                Image(systemName: "waveform.path.ecg")
                    .foregroundColor(.blue)
                Text("健康摘要")
                    .font(.headline)
                Spacer()
                if viewModel.isLoadingContext {
                    ProgressView()
                        .scaleEffect(0.9)
                }
                Button("刷新摘要") {
                    Task { await viewModel.loadContext(force: true) }
                }
                .disabled(viewModel.isLoadingContext)
            }

            Toggle("附带健康摘要", isOn: $includeContext)
                .font(.subheadline)

            DisclosureGroup("摘要内容", isExpanded: $contextExpanded) {
                Group {
                    if let context = viewModel.context {
                        Text(context.summaryText)
                    } else if let error = viewModel.contextError, !error.isEmpty {
                        Text("未能加载摘要：\(error)")
                    } else {
                        Text("尚未加载摘要")
                    }
                }
                .font(.system(.caption, design: .monospaced))
                .foregroundColor(.secondary)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.top, 6)
            }
            .font(.subheadline)
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 4, y: 2)
    }

    private var messagesView: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 10) {
                    ForEach(viewModel.messages) { message in
                        MessageBubble(message: message)
                            .id(message.id)
                    }
                    if viewModel.isSending {
                        MessageBubble(message: AgentMessage(role: .assistant, text: "正在思考…"))
                    }
                }
                .padding(.horizontal)
                .padding(.vertical, 12)
            }
            .onChange(of: viewModel.messages.count) { _, _ in
                guard let lastId = viewModel.messages.last?.id else { return }
                withAnimation(.easeOut(duration: 0.2)) {
                    proxy.scrollTo(lastId, anchor: .bottom)
                }
            }
        }
    }

    private var inputBar: some View {
        VStack(spacing: 8) {
            if !viewModel.attachments.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(viewModel.attachments) { attachment in
                            AttachmentChip(attachment: attachment) {
                                viewModel.removeAttachment(id: attachment.id)
                            }
                        }
                    }
                    .padding(.vertical, 2)
                }
            }

            HStack(spacing: 10) {
                PhotosPicker(selection: $photoItem, matching: .images) {
                    Image(systemName: "photo.on.rectangle")
                        .font(.title3)
                        .foregroundColor(.blue)
                        .padding(8)
                        .background(Color(.secondarySystemBackground))
                        .cornerRadius(8)
                }

                Button {
                    showFileImporter = true
                } label: {
                    Image(systemName: "paperclip")
                        .font(.title3)
                        .foregroundColor(.blue)
                        .padding(8)
                        .background(Color(.secondarySystemBackground))
                        .cornerRadius(8)
                }

                TextField("输入你的问题…", text: $viewModel.inputText)
                    .textFieldStyle(.roundedBorder)
                    .submitLabel(.send)
                    .onSubmit {
                        Task { await viewModel.send(includeContext: includeContext) }
                    }

                Button {
                    Task { await viewModel.send(includeContext: includeContext) }
                } label: {
                    Image(systemName: "paperplane.fill")
                        .foregroundColor(.white)
                        .padding(10)
                        .background(Color.blue)
                        .cornerRadius(10)
                }
                .disabled(sendDisabled)
            }
        }
    }

    private var sendDisabled: Bool {
        if viewModel.isSending { return true }
        if viewModel.attachments.contains(where: { $0.isUploading }) { return true }
        if !viewModel.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { return false }
        return viewModel.attachments.isEmpty
    }

    private func handlePhotoItem(_ item: PhotosPickerItem) async {
        do {
            if let data = try await item.loadTransferable(type: Data.self) {
                let type = item.supportedContentTypes.first
                let ext = type?.preferredFilenameExtension ?? "jpg"
                let mime = type?.preferredMIMEType ?? "image/jpeg"
                let filename = "photo-\(Int(Date().timeIntervalSince1970)).\(ext)"
                await viewModel.addAttachment(
                    data: data,
                    filename: filename,
                    contentType: mime,
                    thumbnailData: data
                )
            }
        } catch {
            viewModel.attachmentError = "读取图片失败：\(error.localizedDescription)"
        }
    }
}

private struct MessageBubble: View {
    let message: AgentMessage

    private var isUser: Bool { message.role == .user }

    var body: some View {
        HStack {
            if isUser { Spacer(minLength: 40) }

            VStack(alignment: .leading, spacing: 8) {
                Text(message.text)
                    .font(.body)
                    .foregroundColor(isUser ? .white : .primary)

                if !message.attachments.isEmpty {
                    VStack(alignment: .leading, spacing: 6) {
                        ForEach(message.attachments) { attachment in
                            AttachmentRow(
                                attachment: attachment,
                                compact: true,
                                textColor: isUser ? .white : .primary
                            )
                        }
                    }
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .background(isUser ? Color.blue : Color(.secondarySystemBackground))
            .cornerRadius(14)
            .frame(maxWidth: 320, alignment: isUser ? .trailing : .leading)

            if !isUser { Spacer(minLength: 40) }
        }
        .frame(maxWidth: .infinity, alignment: isUser ? .trailing : .leading)
    }
}

private struct AttachmentChip: View {
    let attachment: AgentAttachment
    let onRemove: () -> Void

    var body: some View {
        HStack(spacing: 6) {
            AttachmentThumbnail(attachment: attachment, size: 32)

            VStack(alignment: .leading, spacing: 2) {
                Text(attachment.filename)
                    .font(.caption)
                    .lineLimit(1)
                if attachment.isUploading {
                    Text("上传中…")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                } else if let error = attachment.error, !error.isEmpty {
                    Text("失败")
                        .font(.caption2)
                        .foregroundColor(.red)
                }
            }

            Button(action: onRemove) {
                Image(systemName: "xmark.circle.fill")
                    .foregroundColor(.secondary)
            }
        }
        .padding(6)
        .background(Color(.secondarySystemBackground))
        .cornerRadius(10)
    }
}

private struct AttachmentRow: View {
    let attachment: AgentAttachment
    let compact: Bool
    let textColor: Color

    var body: some View {
        HStack(spacing: 8) {
            AttachmentThumbnail(
                attachment: attachment,
                size: compact ? 28 : 36,
                tintColor: textColor
            )
            Text(attachment.filename)
                .font(compact ? .caption : .subheadline)
                .foregroundColor(textColor)
                .lineLimit(1)
        }
    }
}

private struct AttachmentThumbnail: View {
    let attachment: AgentAttachment
    let size: CGFloat
    let tintColor: Color?

    init(attachment: AgentAttachment, size: CGFloat, tintColor: Color? = nil) {
        self.attachment = attachment
        self.size = size
        self.tintColor = tintColor
    }

    var body: some View {
        if attachment.isImage, let data = attachment.thumbnailData, let image = UIImage(data: data) {
            Image(uiImage: image)
                .resizable()
                .scaledToFill()
                .frame(width: size, height: size)
                .clipped()
                .cornerRadius(6)
        } else {
            Image(systemName: "doc.fill")
                .foregroundColor(tintColor ?? .blue)
                .frame(width: size, height: size)
                .background(Color(.tertiarySystemBackground))
                .cornerRadius(6)
        }
    }
}
