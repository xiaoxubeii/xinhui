import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import type { NutritionSummaryResponse } from '@/lib/apiTypes';

interface NutritionDomainProps {
  summary: NutritionSummaryResponse | null;
  isLoading?: boolean;
}

export function NutritionDomain({ summary, isLoading }: NutritionDomainProps) {
  const totals = summary?.totals;

  return (
    <div className="px-6 py-6 space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>热量</CardTitle>
            <CardDescription>kcal</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold text-gray-900">
              {totals ? totals.calories_kcal.toFixed(1) : '—'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>蛋白质</CardTitle>
            <CardDescription>g</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold text-gray-900">
              {totals ? totals.protein_g.toFixed(1) : '—'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>碳水</CardTitle>
            <CardDescription>g</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold text-gray-900">
              {totals ? totals.carbs_g.toFixed(1) : '—'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>脂肪</CardTitle>
            <CardDescription>g</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold text-gray-900">
              {totals ? totals.fat_g.toFixed(1) : '—'}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>每日饮食摘要</CardTitle>
          <CardDescription>
            {summary?.last_diet_entry_at ? `Last entry: ${summary.last_diet_entry_at}` : '—'}
            {summary?.warnings?.length ? ` · Warnings: ${summary.warnings.join(' | ')}` : ''}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {summary?.days?.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Entries</TableHead>
                  <TableHead>Calories</TableHead>
                  <TableHead>Protein</TableHead>
                  <TableHead>Carbs</TableHead>
                  <TableHead>Fat</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {summary.days.map((d) => (
                  <TableRow key={d.date}>
                    <TableCell>{d.date}</TableCell>
                    <TableCell>{d.entry_count}</TableCell>
                    <TableCell>{d.totals.calories_kcal.toFixed(1)}</TableCell>
                    <TableCell>{d.totals.protein_g.toFixed(1)}</TableCell>
                    <TableCell>{d.totals.carbs_g.toFixed(1)}</TableCell>
                    <TableCell>{d.totals.fat_g.toFixed(1)}</TableCell>
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

