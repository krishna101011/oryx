import React, { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Pressable, Skeleton, Spacer, Text } from '@oryx/design-system';
import { usePublicationProvenance } from '../hooks/usePublishing';
import {
  presentProvenance,
  provenanceSummary,
  snapshotNote,
} from '../provenance';

/**
 * "Show your work" — the reader-facing provenance of one publication.
 *
 * Renders the SNAPSHOT the backend took when the publication row was created
 * (publication_citations): intelligence-object headlines with their
 * confidence tier and epistemic type as of the publish moment. Deliberately
 * nothing deeper — no claims, no evidence — matching the publishing layer's
 * public boundary.
 */
export const ProvenanceSection: React.FC<{ publicationId: string }> = ({
  publicationId,
}) => {
  const [expanded, setExpanded] = useState(false);
  const provenance = usePublicationProvenance(publicationId, expanded);

  const entries = provenance.data?.entries ?? [];
  const rows = presentProvenance(entries);

  return (
    <View>
      <Pressable onPress={() => setExpanded((v) => !v)}>
        <Text variant="caption" color="brand">
          {expanded ? 'Hide sources' : 'Show your work →'}
        </Text>
      </Pressable>
      {expanded ? (
        provenance.isLoading ? (
          <>
            <Spacer size={2} />
            <Skeleton height={40} />
          </>
        ) : (
          <>
            <Spacer size={2} />
            <Text variant="caption" color="secondary">
              {provenanceSummary(rows.length)}
            </Text>
            {rows.map((row) => (
              <View key={row.key} style={styles.sourceRow}>
                <Text variant="bodySm">{row.headline}</Text>
                <Text variant="caption" color={row.tone}>
                  {row.tierLabel} · {row.epistemicLabel}
                </Text>
              </View>
            ))}
            {rows.length > 0 ? (
              <>
                <Spacer size={1} />
                <Text variant="caption" color="tertiary">
                  {snapshotNote(entries)}
                </Text>
              </>
            ) : null}
          </>
        )
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  sourceRow: {
    marginTop: 8,
  },
});
