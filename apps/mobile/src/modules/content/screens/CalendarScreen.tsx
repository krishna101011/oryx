import React, { useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import {
  Button,
  Card,
  Screen,
  Skeleton,
  Spacer,
  Text,
  useTheme,
} from '@oryx/design-system';
import type { CalendarEntry } from '@oryx/shared-types';
import type { PublishChannel } from '@oryx/shared-types';
import { ChannelBadge } from '../components/ChannelBadge';
import { useCalendar, useCancelEntry } from '../hooks/useCalendar';
import { useTargets } from '../hooks/usePublishing';
import {
  CALENDAR_STATUS_LABEL,
  calendarStatusColor,
} from '../theme/draftColors';

const WEEKDAYS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

/** Local YYYY-MM-DD key for an ISO timestamp (groups entries by calendar day). */
function dayKey(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

function localDayKey(year: number, month: number, day: number): string {
  return `${year}-${month}-${day}`;
}

function monthLabel(year: number, month: number): string {
  return new Date(year, month, 1).toLocaleDateString(undefined, {
    month: 'long',
    year: 'numeric',
  });
}

function timeLabel(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  });
}

export const CalendarScreen: React.FC = () => {
  const t = useTheme();
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth()); // 0-indexed
  const [selectedDay, setSelectedDay] = useState<number | null>(null);

  // Range covering the whole visible month (inclusive of edge days).
  const rangeStart = useMemo(
    () => new Date(year, month, 1, 0, 0, 0).toISOString(),
    [year, month],
  );
  const rangeEnd = useMemo(
    () => new Date(year, month + 1, 0, 23, 59, 59).toISOString(),
    [year, month],
  );

  const calendar = useCalendar(rangeStart, rangeEnd);
  const cancel = useCancelEntry();
  const targets = useTargets();

  // Resolve targetId → channel so each entry can show its channel badge.
  const channelOf = useMemo(() => {
    const map = new Map<string, PublishChannel>();
    for (const t of targets.data ?? []) map.set(t.id, t.channel);
    return map;
  }, [targets.data]);

  // Group entries by local day-of-month for the dot overlay.
  const byDay = useMemo(() => {
    const map = new Map<string, CalendarEntry[]>();
    for (const e of calendar.data ?? []) {
      const key = dayKey(e.scheduledAt);
      const list = map.get(key) ?? [];
      list.push(e);
      map.set(key, list);
    }
    return map;
  }, [calendar.data]);

  const firstWeekday = new Date(year, month, 1).getDay(); // 0=Sun
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  // Build a flat array of cells: leading blanks + day numbers.
  const cells: (number | null)[] = [
    ...Array.from({ length: firstWeekday }, () => null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];

  const stepMonth = (delta: number) => {
    setSelectedDay(null);
    const next = new Date(year, month + delta, 1);
    setYear(next.getFullYear());
    setMonth(next.getMonth());
  };

  const selectedEntries = selectedDay
    ? byDay.get(localDayKey(year, month, selectedDay)) ?? []
    : [];

  return (
    <Screen>
      <ScrollView showsVerticalScrollIndicator={false}>
      <View style={styles.monthHeader}>
        <Pressable onPress={() => stepMonth(-1)} accessibilityLabel="Previous month">
          <Text variant="h2" color="secondary">
            ‹
          </Text>
        </Pressable>
        <Text variant="h2">{monthLabel(year, month)}</Text>
        <Pressable onPress={() => stepMonth(1)} accessibilityLabel="Next month">
          <Text variant="h2" color="secondary">
            ›
          </Text>
        </Pressable>
      </View>

      <Spacer size={3} />
      <View style={styles.weekRow}>
        {WEEKDAYS.map((w, i) => (
          <View key={`${w}-${i}`} style={styles.cell}>
            <Text variant="caption" color="tertiary">
              {w}
            </Text>
          </View>
        ))}
      </View>

      {calendar.isLoading ? (
        <>
          <Spacer size={3} />
          <Skeleton height={220} />
        </>
      ) : (
        <View style={styles.grid}>
          {cells.map((day, idx) => {
            if (day === null) {
              return <View key={`blank-${idx}`} style={styles.cell} />;
            }
            const entries = byDay.get(localDayKey(year, month, day)) ?? [];
            const sel = day === selectedDay;
            // Up to 3 dots, one per distinct status present that day.
            const statuses = Array.from(
              new Set(entries.map((e) => e.status)),
            ).slice(0, 3);
            return (
              <Pressable
                key={`day-${day}`}
                style={styles.cell}
                onPress={() => setSelectedDay(sel ? null : day)}
              >
                <View
                  style={[
                    styles.dayCell,
                    sel && {
                      backgroundColor: t.colors.accent.tealGlow,
                      borderColor: t.colors.accent.teal,
                    },
                  ]}
                >
                  <Text variant="bodySm" color={entries.length ? 'primary' : 'tertiary'}>
                    {day}
                  </Text>
                  <View style={styles.dots}>
                    {statuses.map((s) => (
                      <View
                        key={s}
                        style={[
                          styles.dot,
                          { backgroundColor: calendarStatusColor(s) },
                        ]}
                      />
                    ))}
                  </View>
                </View>
              </Pressable>
            );
          })}
        </View>
      )}

      {selectedDay !== null && (
        <>
          <Spacer size={4} />
          <Text variant="bodySm" color="secondary">
            {monthLabel(year, month)} {selectedDay}
          </Text>
          <Spacer size={2} />
          {selectedEntries.length === 0 ? (
            <Text variant="caption" color="tertiary">
              Nothing scheduled this day.
            </Text>
          ) : (
            selectedEntries
              .slice()
              .sort((a, b) => a.scheduledAt.localeCompare(b.scheduledAt))
              .map((e) => (
                <Card key={e.id} variant="elevated">
                  <View style={styles.entryRow}>
                    <View style={styles.entryMeta}>
                      <View style={styles.entryHead}>
                        {channelOf.get(e.targetId) && (
                          <ChannelBadge channel={channelOf.get(e.targetId)!} />
                        )}
                        <Text variant="body">{timeLabel(e.scheduledAt)}</Text>
                      </View>
                      <Text
                        variant="caption"
                        style={{ color: calendarStatusColor(e.status) }}
                      >
                        {CALENDAR_STATUS_LABEL[e.status]}
                      </Text>
                    </View>
                    {e.status === 'scheduled' && (
                      <Button
                        label="Cancel"
                        variant="secondary"
                        loading={cancel.isPending}
                        onPress={() => cancel.mutate(e.id)}
                      />
                    )}
                  </View>
                </Card>
              ))
          )}
        </>
      )}
      <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const styles = StyleSheet.create({
  cell: {
    alignItems: 'center',
    width: `${100 / 7}%`,
  },
  dayCell: {
    alignItems: 'center',
    borderColor: 'transparent',
    borderRadius: 10,
    borderWidth: 1,
    minHeight: 48,
    justifyContent: 'center',
    paddingVertical: 6,
    width: '92%',
  },
  dot: {
    borderRadius: 3,
    height: 6,
    marginHorizontal: 1,
    width: 6,
  },
  dots: {
    flexDirection: 'row',
    marginTop: 4,
    minHeight: 6,
  },
  entryHead: { alignItems: 'center', flexDirection: 'row', gap: 8 },
  entryMeta: { gap: 4 },
  entryRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    rowGap: 4,
  },
  monthHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  weekRow: {
    flexDirection: 'row',
  },
});
