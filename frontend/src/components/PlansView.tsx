import { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw, Dumbbell, Utensils } from 'lucide-react';
import { Button } from '@/components/ui/button';

const apiBase = import.meta.env.VITE_API_BASE ?? '';

async function apiFetch(path: string, init?: RequestInit) {
  return fetch(`${apiBase}${path}`, {
    credentials: 'include',
    ...init,
  });
}

interface ExercisePlan {
  plan_id: string;
  title?: string | null;
  summary: string;
  sessions: Array<{
    type?: string | null;
    duration_min?: number | null;
    intensity?: string | null;
    kcal_est?: number | null;
    notes?: string | null;
  }>;
  goals?: Record<string, unknown> | null;
  generated_at?: string | null;
  valid_from?: string | null;
  valid_to?: string | null;
}

interface NutritionPlan {
  plan_id: string;
  title?: string | null;
  summary: string;
  macros?: Record<string, unknown> | null;
  meals: Array<{
    meal_type?: string | null;
    kcal?: number | null;
    foods?: string[] | null;
  }>;
  constraints?: Record<string, unknown> | null;
  generated_at?: string | null;
  valid_from?: string | null;
  valid_to?: string | null;
}

const toLocalDate = (iso?: string | null) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
};

export function PlansView({ userId }: { userId: string }) {
  const [exercisePlan, setExercisePlan] = useState<ExercisePlan | null>(null);
  const [nutritionPlan, setNutritionPlan] = useState<NutritionPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPlans = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    try {
      const [exerciseResp, nutritionResp] = await Promise.all([
        apiFetch(`/api/plans/exercise/${encodeURIComponent(userId)}`),
        apiFetch(`/api/plans/nutrition/${encodeURIComponent(userId)}`),
      ]);

      if (exerciseResp.status === 404) {
        setExercisePlan(null);
      } else if (exerciseResp.ok) {
        setExercisePlan((await exerciseResp.json()) as ExercisePlan);
      } else {
        throw new Error(`加载运动处方失败 (${exerciseResp.status})`);
      }

      if (nutritionResp.status === 404) {
        setNutritionPlan(null);
      } else if (nutritionResp.ok) {
        setNutritionPlan((await nutritionResp.json()) as NutritionPlan);
      } else {
        throw new Error(`加载营养规划失败 (${nutritionResp.status})`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    void loadPlans();
  }, [loadPlans]);

  const exerciseRange = useMemo(() => {
    if (!exercisePlan) return '—';
    return `${toLocalDate(exercisePlan.valid_from)} - ${toLocalDate(exercisePlan.valid_to)}`;
  }, [exercisePlan]);

  const nutritionRange = useMemo(() => {
    if (!nutritionPlan) return '—';
    return `${toLocalDate(nutritionPlan.valid_from)} - ${toLocalDate(nutritionPlan.valid_to)}`;
  }, [nutritionPlan]);

  const exerciseGoals = (exercisePlan?.goals ?? {}) as Record<string, unknown>;
  const nutritionMacros = (nutritionPlan?.macros ?? {}) as Record<string, unknown>;
  const nutritionConstraints = (nutritionPlan?.constraints ?? {}) as Record<string, unknown>;

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6">
      <div className="max-w-[900px] mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-lg font-semibold text-gray-900">运动与营养规划</div>
            <div className="text-xs text-gray-500 mt-1">展示最近确认的运动处方与营养规划</div>
          </div>
          <Button type="button" variant="outline" onClick={() => void loadPlans()} disabled={loading}>
            <RefreshCw className="w-4 h-4" />
            刷新
          </Button>
        </div>

        {error && (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700">
            {error}
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="border border-gray-200 rounded-2xl p-5 bg-white">
            <div className="flex items-center gap-2 text-sm font-semibold text-gray-900">
              <Dumbbell className="w-4 h-4 text-gray-500" />
              运动处方
            </div>
            {exercisePlan ? (
              <div className="mt-4 space-y-4 text-sm text-gray-700">
                <div>
                  <div className="text-xs text-gray-400">方案</div>
                  <div className="text-sm text-gray-900">{exercisePlan.title ?? '运动处方'}</div>
                  <div className="text-xs text-gray-500 mt-1">{exercisePlan.summary}</div>
                </div>
                <div className="text-xs text-gray-500">有效期：{exerciseRange}</div>
                <div className="text-xs text-gray-500">
                  确认时间：{toLocalDate(exercisePlan.generated_at)}
                </div>
                <div className="text-xs text-gray-600 space-y-1">
                  <div>
                    目标：步数 {String(exerciseGoals.steps_target ?? '—')} · 时长{' '}
                    {String(exerciseGoals.minutes_target ?? '—')} 分钟 · 消耗{' '}
                    {String(exerciseGoals.kcal_target ?? '—')} kcal · 心率区间{' '}
                    {String(exerciseGoals.hr_zone ?? '—')}
                  </div>
                  <div>计划条目：{exercisePlan.sessions.length} 条</div>
                </div>
                {exercisePlan.sessions.length > 0 && (
                  <div className="space-y-2 text-xs text-gray-600">
                    {exercisePlan.sessions.map((item, idx) => (
                      <div key={`${item.type ?? 'session'}-${idx}`} className="rounded-xl bg-gray-50 px-3 py-2">
                        <div>
                          {item.type ?? '训练'} · {item.duration_min ?? '—'} 分钟 ·{' '}
                          {item.intensity ?? '—'} · {item.kcal_est ?? '—'} kcal
                        </div>
                        {item.notes && <div className="text-[11px] text-gray-500 mt-1">{item.notes}</div>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="mt-4 text-xs text-gray-500">暂无已确认的运动处方。</div>
            )}
          </div>

          <div className="border border-gray-200 rounded-2xl p-5 bg-white">
            <div className="flex items-center gap-2 text-sm font-semibold text-gray-900">
              <Utensils className="w-4 h-4 text-gray-500" />
              营养规划
            </div>
            {nutritionPlan ? (
              <div className="mt-4 space-y-4 text-sm text-gray-700">
                <div>
                  <div className="text-xs text-gray-400">方案</div>
                  <div className="text-sm text-gray-900">{nutritionPlan.title ?? '营养规划'}</div>
                  <div className="text-xs text-gray-500 mt-1">{nutritionPlan.summary}</div>
                </div>
                <div className="text-xs text-gray-500">有效期：{nutritionRange}</div>
                <div className="text-xs text-gray-500">
                  确认时间：{toLocalDate(nutritionPlan.generated_at)}
                </div>
                <div className="text-xs text-gray-600">
                  宏量：热量 {String(nutritionMacros.kcal ?? '—')} kcal · 蛋白{' '}
                  {String(nutritionMacros.protein_g ?? '—')} g · 碳水{' '}
                  {String(nutritionMacros.carbs_g ?? '—')} g · 脂肪{' '}
                  {String(nutritionMacros.fat_g ?? '—')} g
                </div>
                {nutritionPlan.meals.length > 0 && (
                  <div className="space-y-2 text-xs text-gray-600">
                    {nutritionPlan.meals.map((meal, idx) => (
                      <div key={`${meal.meal_type ?? 'meal'}-${idx}`} className="rounded-xl bg-gray-50 px-3 py-2">
                        <div>
                          {meal.meal_type ?? `餐次${idx + 1}`}：{meal.kcal ?? '—'} kcal
                        </div>
                        {meal.foods && meal.foods.length > 0 && (
                          <div className="text-[11px] text-gray-500 mt-1">{meal.foods.join('、')}</div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                <div className="text-xs text-gray-600">
                  约束：控糖 {String(nutritionConstraints.low_sugar ?? '—')} · 控盐{' '}
                  {String(nutritionConstraints.low_salt ?? '—')} · 高纤维{' '}
                  {String(nutritionConstraints.high_fiber ?? '—')}
                </div>
              </div>
            ) : (
              <div className="mt-4 text-xs text-gray-500">暂无已确认的营养规划。</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
