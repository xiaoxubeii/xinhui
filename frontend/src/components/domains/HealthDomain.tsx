import { useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import type { HealthSummaryResponse } from '@/lib/apiTypes';

interface HealthDomainProps {
  summary: HealthSummaryResponse | null;
  isLoading?: boolean;
}

function mean(values: Array<number | null | undefined>): number | null {
  const filtered = values.filter((v): v is number => typeof v === 'number' && Number.isFinite(v));
  if (filtered.length === 0) {
    return null;
  }
  return filtered.reduce((a, b) => a + b, 0) / filtered.length;
}

export function HealthDomain({ summary, isLoading }: HealthDomainProps) {
  const totals = useMemo(() => {
    const days = summary?.days ?? [];
    const totalSleep = days.reduce((acc, d) => acc + (d.sleep_hours ?? 0), 0);
    const resting = mean(days.map((d) => d.resting_hr_avg_bpm));
    const hrAvg = mean(days.map((d) => d.hr_avg_bpm));
    const hrMax = Math.max(...days.map((d) => (typeof d.hr_max_bpm === 'number' ? d.hr_max_bpm : 0)));
    const spo2 = mean(days.map((d) => d.spo2_avg_pct));
    return {
      totalSleep: Number.isFinite(totalSleep) ? totalSleep : 0,
      resting,
      hrAvg,
      hrMax: hrMax > 0 ? hrMax : null,
      spo2,
    };
  }, [summary]);

  return (
    <div className="px-6 py-6 space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>总睡眠</CardTitle>
            <CardDescription>小时</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold text-gray-900">{totals.totalSleep.toFixed(1)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>静息心率</CardTitle>
            <CardDescription>均值 bpm</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold text-gray-900">
              {totals.resting !== null ? totals.resting.toFixed(1) : '—'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>日均心率</CardTitle>
            <CardDescription>均值 bpm</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold text-gray-900">
              {totals.hrAvg !== null ? totals.hrAvg.toFixed(1) : '—'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>血氧</CardTitle>
            <CardDescription>均值 %</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold text-gray-900">
              {totals.spo2 !== null ? totals.spo2.toFixed(1) : '—'}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>每日健康摘要</CardTitle>
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
                  <TableHead>Sleep (h)</TableHead>
                  <TableHead>Rest HR</TableHead>
                  <TableHead>HR avg</TableHead>
                  <TableHead>HR max</TableHead>
                  <TableHead>SpO2</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {summary.days.map((d) => (
                  <TableRow key={d.date}>
                    <TableCell>{d.date}</TableCell>
                    <TableCell>{(d.sleep_hours ?? 0).toFixed(2)}</TableCell>
                    <TableCell>{d.resting_hr_avg_bpm !== null ? d.resting_hr_avg_bpm.toFixed(1) : '—'}</TableCell>
                    <TableCell>{d.hr_avg_bpm !== null ? d.hr_avg_bpm.toFixed(1) : '—'}</TableCell>
                    <TableCell>{d.hr_max_bpm !== null ? d.hr_max_bpm.toFixed(1) : '—'}</TableCell>
                    <TableCell>{d.spo2_avg_pct !== null ? d.spo2_avg_pct.toFixed(1) : '—'}</TableCell>
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

