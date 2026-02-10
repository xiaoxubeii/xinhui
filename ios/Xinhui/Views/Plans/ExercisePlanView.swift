import SwiftUI

struct ExercisePlanView: View {
    let plan: ExercisePlanResponse?

    var body: some View {
        List {
            Section(header: Text("摘要")) {
                Text(plan?.summary ?? "暂无处方")
            }

            if let goals = plan?.goals {
                Section(header: Text("目标")) {
                    if let steps = goals.stepsTarget { Text("步数目标：\(steps) 步") }
                    if let minutes = goals.minutesTarget { Text(String(format: "运动时长：%.0f 分钟", minutes)) }
                    if let kcal = goals.kcalTarget { Text(String(format: "消耗目标：%.0f kcal", kcal)) }
                    if let hr = goals.hrZone { Text("心率区间：\(hr)") }
                }
            }

            if let sessions = plan?.sessions, !sessions.isEmpty {
                Section(header: Text("处方计划")) {
                    ForEach(sessions) { session in
                        VStack(alignment: .leading, spacing: 6) {
                            Text(session.type ?? "运动")
                                .font(.headline)
                            if let duration = session.durationMin {
                                Text(String(format: "时长：%.0f 分钟", duration))
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            if let intensity = session.intensity {
                                Text("强度：\(intensity)")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            if let kcal = session.kcalEst {
                                Text(String(format: "预计消耗：%.0f kcal", kcal))
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            if let notes = session.notes, !notes.isEmpty {
                                Text(notes)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                }
            }
        }
        .navigationTitle(plan?.title ?? "运动处方")
    }
}
