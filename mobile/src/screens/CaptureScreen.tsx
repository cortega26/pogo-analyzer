import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Image,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import AsyncStorage from "@react-native-async-storage/async-storage";

const STORAGE_KEY = "@pogo_analyzer_recent_scans";
const MAX_HISTORY = 12;
const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? process.env.API_BASE_URL ?? "http://localhost:8000";

type ScanResult = {
  name: string;
  form: string;
  ivs: [number, number, number];
  level: number;
};

type ScanHistoryEntry = {
  id: string;
  imageUri: string;
  timestamp: string;
  result: ScanResult;
};

const emptyResult: ScanResult | null = null;

const toScanResult = (payload: any): ScanResult => ({
  name: String(payload?.name ?? ""),
  form: String(payload?.form ?? ""),
  ivs: [0, 1, 2].map((index) => Number(payload?.ivs?.[index] ?? 0)) as [
    number,
    number,
    number
  ],
  level: Number(payload?.level ?? 0),
});

const formatTimestamp = (value: string): string => {
  try {
    return new Date(value).toLocaleString();
  } catch (error) {
    return value;
  }
};

const CaptureScreen: React.FC = () => {
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<ScanResult | null>(emptyResult);
  const [history, setHistory] = useState<ScanHistoryEntry[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const stored = await AsyncStorage.getItem(STORAGE_KEY);
        if (stored) {
          const parsed = JSON.parse(stored) as ScanHistoryEntry[];
          setHistory(parsed);
        }
      } catch (error) {
        console.warn("Failed to load cached scans", error);
      }
    };

    void bootstrap();
  }, []);

  useEffect(() => {
    const requestPermissions = async () => {
      const camera = await ImagePicker.requestCameraPermissionsAsync();
      const media = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (camera.status !== "granted" || media.status !== "granted") {
        Alert.alert(
          "Permissions required",
          "Camera and media permissions are needed to analyse screenshots.",
        );
      }
    };

    void requestPermissions();
  }, []);

  const persistHistory = useCallback((entries: ScanHistoryEntry[]) => {
    void AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  }, []);

  const capture = useCallback(async () => {
    const result = await ImagePicker.launchCameraAsync({ quality: 0.8, base64: false });
    if (result.canceled) {
      return;
    }

    const uri = result.assets?.[0]?.uri;
    if (uri) {
      setImageUri(uri);
      setAnalysis(emptyResult);
    }
  }, []);

  const pickFromLibrary = useCallback(async () => {
    const result = await ImagePicker.launchImageLibraryAsync({ quality: 0.8, base64: false });
    if (result.canceled) {
      return;
    }
    const uri = result.assets?.[0]?.uri;
    if (uri) {
      setImageUri(uri);
      setAnalysis(emptyResult);
    }
  }, []);

  const submitForAnalysis = useCallback(async () => {
    if (!imageUri) {
      Alert.alert("No screenshot", "Capture or select a screenshot first.");
      return;
    }

    const fileName = imageUri.split("/").pop() ?? "screenshot.png";
    const form = new FormData();
    form.append(
      "file",
      {
        uri: imageUri,
        name: fileName,
        type: "image/png",
      } as unknown as any,
    );

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/scan`, {
        method: "POST",
        body: form,
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || "Unable to analyse screenshot.");
      }

      const payload = await response.json();
      const parsed = toScanResult(payload);
      setAnalysis(parsed);

      const entry: ScanHistoryEntry = {
        id: `${Date.now()}`,
        imageUri,
        timestamp: new Date().toISOString(),
        result: parsed,
      };

      setHistory((previous) => {
        const filtered = previous.filter((item) => item.imageUri !== entry.imageUri);
        const updated = [entry, ...filtered].slice(0, MAX_HISTORY);
        persistHistory(updated);
        return updated;
      });
    } catch (error: any) {
      Alert.alert("Analysis failed", error?.message ?? "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [imageUri, persistHistory]);

  const handleSelectHistory = useCallback((entry: ScanHistoryEntry) => {
    setAnalysis(entry.result);
    setImageUri(entry.imageUri);
  }, []);

  const analysisView = useMemo(() => {
    if (!analysis) {
      return (
        <Text style={styles.placeholderText}>
          Capture or select a screenshot to analyse it.
        </Text>
      );
    }

    const levelDisplay = Number.isFinite(analysis.level)
      ? analysis.level.toFixed(1)
      : "?";

    return (
      <View style={styles.analysisCard}>
        <Text style={styles.analysisTitle}>{analysis.name}</Text>
        <Text style={styles.analysisSubtitle}>Form: {analysis.form || "Normal"}</Text>
        <Text style={styles.analysisDetail}>IVs: {analysis.ivs.join(" / ")}</Text>
        <Text style={styles.analysisDetail}>Level: {levelDisplay}</Text>
      </View>
    );
  }, [analysis]);

  const renderHistoryItem = useCallback(({ item }: { item: ScanHistoryEntry }) => (
    <TouchableOpacity
      onPress={() => handleSelectHistory(item)}
      style={[styles.historyItem, styles.historyItemSpacing]}
    >
      <Image source={{ uri: item.imageUri }} style={styles.historyThumbnail} />
      <View style={styles.historyTextContainer}>
        <Text style={styles.historyTitle}>{item.result.name}</Text>
        <Text style={[styles.historySubtitle, styles.historyTextSpacing]}>
          {item.result.form || "Normal"}
        </Text>
        <Text style={[styles.historyMeta, styles.historyTextSpacing]}>
          {formatTimestamp(item.timestamp)}
        </Text>
      </View>
    </TouchableOpacity>
  ), [handleSelectHistory]);

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.previewContainer}>
          {imageUri ? (
            <Image source={{ uri: imageUri }} style={styles.previewImage} />
          ) : (
            <Text style={styles.placeholderText}>No screenshot selected.</Text>
          )}
        </View>

        <View style={styles.buttonRow}>
          <TouchableOpacity onPress={capture} style={[styles.button, styles.buttonSpacing]}>
            <Text style={styles.buttonLabel}>Capture</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={pickFromLibrary} style={[styles.button, styles.buttonSpacing]}>
            <Text style={styles.buttonLabel}>Select</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={submitForAnalysis} style={styles.primaryButton}>
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.primaryButtonLabel}>Analyze</Text>
            )}
          </TouchableOpacity>
        </View>

        <View style={styles.analysisContainer}>{analysisView}</View>

        <Text style={styles.historyHeading}>Recent scans</Text>
        {history.length === 0 ? (
          <Text style={styles.placeholderText}>Scans will be cached here for offline review.</Text>
        ) : (
          <FlatList
            data={history}
            keyExtractor={(item) => item.id}
            renderItem={renderHistoryItem}
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.historyList}
          />
        )}
      </ScrollView>
    </SafeAreaView>
  );
};

export default CaptureScreen;

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#0f172a",
  },
  container: {
    padding: 16,
  },
  previewContainer: {
    height: 280,
    borderRadius: 12,
    backgroundColor: "#1e293b",
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  previewImage: {
    width: "100%",
    height: "100%",
    resizeMode: "cover",
  },
  placeholderText: {
    color: "#cbd5f5",
    textAlign: "center",
  },
  buttonRow: {
    flexDirection: "row",
    marginTop: 16,
  },
  button: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: "#334155",
    alignItems: "center",
  },
  buttonLabel: {
    color: "#f8fafc",
    fontWeight: "600",
  },
  primaryButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: "#2563eb",
    alignItems: "center",
    justifyContent: "center",
  },
  primaryButtonLabel: {
    color: "#f8fafc",
    fontWeight: "700",
  },
  analysisContainer: {
    marginTop: 24,
    padding: 16,
    borderRadius: 12,
    backgroundColor: "#1e293b",
  },
  analysisCard: {
  },
  analysisTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: "#f8fafc",
  },
  analysisSubtitle: {
    color: "#cbd5f5",
    marginTop: 4,
  },
  analysisDetail: {
    color: "#e2e8f0",
    marginTop: 4,
  },
  historyHeading: {
    marginTop: 24,
    fontSize: 16,
    fontWeight: "600",
    color: "#f8fafc",
  },
  historyList: {
    paddingVertical: 12,
    paddingRight: 12,
  },
  historyItem: {
    width: 160,
    backgroundColor: "#1e293b",
    borderRadius: 12,
    overflow: "hidden",
  },
  historyItemSpacing: {
    marginRight: 12,
  },
  historyThumbnail: {
    width: "100%",
    height: 110,
  },
  historyTextContainer: {
    padding: 12,
  },
  historyTitle: {
    fontWeight: "600",
    color: "#f8fafc",
  },
  historySubtitle: {
    color: "#cbd5f5",
  },
  historyMeta: {
    color: "#94a3b8",
    fontSize: 12,
  },
  historyTextSpacing: {
    marginTop: 4,
  },
  buttonSpacing: {
    marginRight: 12,
  },
});
