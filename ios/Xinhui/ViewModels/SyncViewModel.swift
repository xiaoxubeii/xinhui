import Foundation
import Combine

@MainActor
final class SyncViewModel: ObservableObject {
    @Published var selectedTypes: Set<HealthDataType> = Set(HealthDataType.allCases)
    @Published var startDate: Date = Calendar.current.date(byAdding: .day, value: -30, to: Date())!
    @Published var endDate: Date = Date()
    @Published var progress = SyncProgress()
    @Published var isSyncing = false
    @Published var currentError: SyncError?
    @Published var lastResponse: HealthSyncResponse?

    private let coordinator: SyncCoordinator

    init(coordinator: SyncCoordinator = SyncCoordinator()) {
        self.coordinator = coordinator
    }

    func startSync() {
        guard !isSyncing else { return }
        isSyncing = true
        currentError = nil
        lastResponse = nil
        progress = SyncProgress()

        Task {
            do {
                let response = try await coordinator.performSync(
                    dataTypes: selectedTypes,
                    dateRange: startDate...endDate,
                    onProgress: { [weak self] p in
                        Task { @MainActor in self?.progress = p }
                    }
                )
                lastResponse = response
            } catch is CancellationError {
                currentError = nil
                progress.phase = .idle
            } catch let error as SyncError {
                currentError = error
                progress.phase = .failed
            } catch {
                currentError = .networkError(underlying: error)
                progress.phase = .failed
            }
            isSyncing = false
        }
    }
}
