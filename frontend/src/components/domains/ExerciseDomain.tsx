import { useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import type { ExerciseSummaryResponse } from '@/lib/apiTypes';

interface ExerciseDomainProps {
  summary: ExerciseSummaryResponse | null;
  isLoading?: boolean;
}

export function ExerciseDomain({ summary, isLoading }: ExerciseDomainProps) {
  const totals = useMemo(() => {
    const days = summary?.days ?? [];
    const steps = days.reduce((acc, d) => acc + (d.steps ?? 0), 0);
    const kcal = days.reduce((acc, d) => acc + (d.workout_energy_kcal ?? 0), 0);
    const count = days.reduce((acc, d) => acc + (d.workout_count ?? 0), 0);
    return { steps, kcal, count };
  }, [summary]);

  return (
    <div className="px-6 py-6 space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>总步数</CardTitle>
            <CardDescription>范围内累计</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold text-gray-900">{totals.steps.toLocaleString()}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>运动消耗</CardTitle>
            <CardDescription>kcal</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold text-gray-900">{totals.kcal.toFixed(1)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Workout 次数</CardTitle>
            <CardDescription>范围内累计</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold text-gray-900">{totals.count}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>每日运动摘要</CardTitle>
          <CardDescription>
            {summary?.last_healthkit_sync_at ? `Last sync: ${summary.last_healthkit_sync_at}` : '—'}
            {summary?.warnings?.length ? ` · Warnings: ${summary.warnings.join(' | ')}` : ''}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {summary?.days?.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Steps</TableHead>
                  <TableHead>Workout kcal</TableHead>
                  <TableHead>Workout count</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {summary.days.map((d) => (
                  <TableRow key={d.date}>
                    <TableCell>{d.date}</TableCell>
                    <TableCell>{d.steps.toLocaleString()}</TableCell>
                    <TableCell>{d.workout_energy_kcal.toFixed(1)}</TableCell>
                    <TableCell>{d.workout_count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : isLoading ? (
            <div className="text-sm text-gray-500">加载中…</div>
          ) : (
            <div className="text-sm text-gray-500">暂无数据</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

