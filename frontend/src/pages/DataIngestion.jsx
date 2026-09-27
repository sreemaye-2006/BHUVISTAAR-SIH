import React, { useState, useRef } from "react";
import {
  Upload,
  Map,
  Building2,
  FileText,
  Navigation,
  Satellite,
  Mountain,
  Database,
  CheckCircle2,
  AlertCircle,
  Eye,
  Loader2,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import { createDataset, uploadDatasetFile, inspectDataset } from "../api/datasets";
import { processVectorDataset, processRaster } from "../api/gis";
import IngestionPreviewModal from "../components/ingestion/IngestionPreviewModal";

const RASTER_EXTS = ["tif", "tiff", "dem", "img", "jpg", "jpeg", "png"];
const ALL_SUPPORTED_MIME = ".geojson,.json,.shp,.zip,.kml,.kmz,.gpkg,.gpx,.csv,.xlsx,.xls,.tif,.tiff,.jpg,.jpeg,.png";

function DataIngestion() {
  const { t } = useTranslation();
  const { selectedProjectId } = useAuth();
  const fileInputRef = useRef(null);
  const [selectedSourceForUpload, setSelectedSourceForUpload] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [uploadQueue, setUploadQueue] = useState([]);
  const [isUploading, setIsUploading] = useState(false);

  // Inspection modal state
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewMetadata, setPreviewMetadata] = useState(null);
  const [previewFileName, setPreviewFileName] = useState("");

  const dataSources = [
    { id: "drone", name: t("ingestion.droneSurvey", "Drone Survey"), description: t("ingestion.droneDesc", "Orthophoto, point clouds & aerial building footprints"), icon: Upload, formats: "GeoTIFF, SHP, GeoJSON", acceptedMime: ".tif,.tiff,.shp,.geojson,.zip,.kml" },
    { id: "ori", name: t("ingestion.ori", "ORI"), description: t("ingestion.oriDesc", "High-resolution orthorectified satellite/aerial imagery"), icon: Satellite, formats: "GeoTIFF, JPEG, PNG", acceptedMime: ".tif,.tiff,.jpg,.jpeg,.png" },
    { id: "cadastral", name: t("ingestion.cadastral", "Cadastral"), description: t("ingestion.cadastralDesc", "Revenue parcel boundaries and village map sheets"), icon: Map, formats: "SHP, GeoJSON, GPKG, KML", acceptedMime: ".shp,.geojson,.gpkg,.zip,.kml,.kmz,.json" },
    { id: "municipal", name: t("ingestion.municipal", "Municipal GIS"), description: t("ingestion.municipalDesc", "Property tax polygons, building IDs & civic attributes"), icon: Building2, formats: "SHP, GeoJSON, CSV, GPKG", acceptedMime: ".shp,.geojson,.csv,.json,.zip,.gpkg" },
    { id: "revenue", name: t("ingestion.revenue", "Revenue Records"), description: t("ingestion.revenueDesc", "Ownership register, RoR / Jamabandi & mutation data"), icon: FileText, formats: "CSV, XLSX, XLS", acceptedMime: ".csv,.xlsx,.xls" },
    { id: "gnss", name: t("ingestion.gnss", "GNSS / CORS"), description: t("ingestion.gnssDesc", "High-precision rover survey coordinates & GCP benchmarks"), icon: Navigation, formats: "GPX, CSV, GPKG", acceptedMime: ".gpx,.csv,.txt,.gpkg" },
    { id: "ground_truth", name: t("ingestion.groundTruth", "Ground Truth"), description: t("ingestion.groundTruthDesc", "Field survey ground-truthing & physical verification logs"), icon: Database, formats: "CSV, GeoJSON, GPX", acceptedMime: ".csv,.geojson,.json,.gpx" },
    { id: "dsm", name: t("ingestion.dsm", "DSM / DTM"), description: t("ingestion.dsmDesc", "Digital Surface Model & elevation contours"), icon: Mountain, formats: "GeoTIFF, TIFF", acceptedMime: ".tif,.tiff" },
  ];

  const showToast = (message, type = "success") => {
    setToastMessage({ text: message, type });
    setTimeout(() => setToastMessage(null), 4000);
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const handleUploadFiles = async (files, forcedSource = null) => {
    if (!files || files.length === 0) return;
    if (!selectedProjectId) {
      showToast(t("ingestion.selectProjectFirst", "Please select or create a project first from the top header."), "error");
      return;
    }

    setIsUploading(true);
    const fileList = Array.from(files);

    for (const file of fileList) {
      const ext = file.name.split(".").pop().toLowerCase();
      const isRaster = RASTER_EXTS.includes(ext);
      const sourceType = forcedSource ? forcedSource.id : (isRaster ? "drone" : "cadastral");
      const datasetType = isRaster ? "raster" : "vector";

      const queueId = "temp-" + Date.now();
      const queueItem = {
        id: queueId,
        datasetId: null,
        name: file.name,
        size: formatFileSize(file.size),
        source: forcedSource ? forcedSource.name : "Uploaded Data",
        status: "Uploading...",
        progress: 0,
        crs: "Auto-detecting...",
      };

      setUploadQueue((prev) => [queueItem, ...prev]);

      try {
        // 1. Create dataset record in backend DB
        const dataset = await createDataset(selectedProjectId, file.name, datasetType, sourceType);

        // 2. Upload file to backend server
        await uploadDatasetFile(dataset.id, file, (percent) => {
          setUploadQueue((prev) =>
            prev.map((item) => (item.id === queueId ? { ...item, progress: percent, status: `Uploading ${percent}%` } : item))
          );
        });

        // 3. Trigger GIS processing / inspection
        setUploadQueue((prev) =>
          prev.map((item) => (item.id === queueId ? { ...item, status: "Processing GIS features..." } : item))
        );

        let processRes = null;
        if (datasetType === "vector") {
          processRes = await processVectorDataset(dataset.id);
        } else {
          try {
            processRes = await processRaster(dataset.id);
          } catch (rErr) {
            console.warn("Raster note:", rErr);
            processRes = { status: "unreferenced" };
          }
        }

        // 4. Try inspecting metadata
        let inspection = null;
        try {
          inspection = await inspectDataset(dataset.id);
        } catch (e) {
          // Non-blocking inspection attempt
        }

        setUploadQueue((prev) =>
          prev.map((item) =>
            item.id === queueId
              ? {
                  ...item,
                  id: dataset.id,
                  datasetId: dataset.id,
                  status: "Completed",
                  crs: inspection?.crs || processRes?.crs || "EPSG:4326",
                  format: inspection?.format || ext.toUpperCase(),
                  featuresCount: inspection?.feature_count !== undefined ? `${inspection.feature_count} records` : (processRes?.feature_count ? `${processRes.feature_count} features` : "Processed"),
                  metadata: inspection,
                }
              : item
          )
        );

        showToast(`"${file.name}" ${t("ingestion.uploadSuccess", "uploaded and processed successfully!")}`);
      } catch (err) {
        setUploadQueue((prev) =>
          prev.map((item) => (item.id === queueId ? { ...item, status: "Failed", error: err.friendlyMessage || err.message } : item))
        );
        showToast(`${t("ingestion.uploadFailed", "Failed to process")} "${file.name}": ${err.friendlyMessage || err.message}`, "error");
      }
    }
    setIsUploading(false);
  };

  const handleOpenInspect = (item) => {
    if (item.metadata) {
      setPreviewMetadata(item.metadata);
      setPreviewFileName(item.name);
      setPreviewModalOpen(true);
    } else if (item.datasetId) {
      inspectDataset(item.datasetId)
        .then((data) => {
          setPreviewMetadata(data);
          setPreviewFileName(item.name);
          setPreviewModalOpen(true);
        })
        .catch(() => {
          showToast("Could not load dataset inspection metadata.", "error");
        });
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === "dragenter" || e.type === "dragover");
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files) {
      handleUploadFiles(e.dataTransfer.files, selectedSourceForUpload);
    }
  };

  const triggerGenericUpload = () => {
    setSelectedSourceForUpload(null);
    if (fileInputRef.current) {
      fileInputRef.current.accept = ALL_SUPPORTED_MIME;
      fileInputRef.current.click();
    }
  };

  const triggerSourceUpload = (source) => {
    setSelectedSourceForUpload(source);
    if (fileInputRef.current) {
      fileInputRef.current.accept = source.acceptedMime;
      fileInputRef.current.click();
    }
  };

  return (
    <div className="space-y-6">
      {/* Toast */}
      {toastMessage && (
        <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-2.5 px-4 py-2.5 rounded-lg border shadow-md text-xs font-semibold ${
          toastMessage.type === "error" ? "bg-red-50 text-red-800 border-red-200" : "bg-emerald-50 text-[#166534] border-emerald-200"
        }`}>
          {toastMessage.type === "error" ? <AlertCircle size={16} /> : <CheckCircle2 size={16} />}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Inspection Modal */}
      <IngestionPreviewModal
        isOpen={previewModalOpen}
        onClose={() => setPreviewModalOpen(false)}
        metadata={previewMetadata}
        fileName={previewFileName}
      />

      <input type="file" ref={fileInputRef} onChange={(e) => handleUploadFiles(e.target.files, selectedSourceForUpload)} multiple className="hidden" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            {t("ingestion.title", "Data Ingestion")}
          </h1>
          <p className="text-xs text-slate-500 font-normal mt-0.5">
            {t("ingestion.subtitle", "Upload real multi-source geospatial files directly to PostgreSQL/PostGIS.")}
          </p>
        </div>
      </div>

      {/* Drag & Drop Area */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
          dragActive ? "border-[#166534] bg-emerald-50/50" : "border-slate-300 bg-white hover:border-slate-400"
        }`}
      >
        <div className="w-10 h-10 mx-auto rounded-lg bg-emerald-50 text-[#166534] flex items-center justify-center mb-3">
          {isUploading ? <Loader2 size={20} className="animate-spin text-emerald-600" /> : <Upload size={20} />}
        </div>

        <h2 className="text-sm font-bold text-slate-900">
          {t("ingestion.dragDropTitle", "Upload Multi-Format Geospatial Datasets")}
        </h2>
        <p className="text-xs text-slate-500 max-w-lg mx-auto mt-1">
          {t("ingestion.dragDropDesc", "Drag & drop or browse: GeoJSON, Shapefile (.shp / .zip), KML, KMZ, GeoPackage (.gpkg), GPX, CSV, Excel (.xlsx / .xls), GeoTIFF, JPG or PNG.")}
        </p>

        <div className="mt-4 flex items-center justify-center gap-3">
          <button
            onClick={triggerGenericUpload}
            disabled={isUploading}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#166534] hover:bg-emerald-900 text-white rounded-md text-xs font-semibold transition-colors cursor-pointer disabled:opacity-50 shadow-sm"
          >
            <Upload size={14} />
            {isUploading ? t("common.loading", "Uploading...") : t("ingestion.selectFiles", "Select Files")}
          </button>
        </div>

        <span className="mt-3 block text-[11px] text-slate-400">
          {t("ingestion.maxSizeNotice", "Max file size: 500 MB • Multi-format Parsers • UTM CRS Detection • Safe Extraction")}
        </span>
      </div>

      {/* Recent Ingestion Stream Queue */}
      {uploadQueue.length > 0 && (
        <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-3 shadow-2xs">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <h3 className="text-sm font-bold text-slate-900">
              {t("ingestion.recentStream", "Recent Ingestion Stream")}
            </h3>
            <button onClick={() => setUploadQueue([])} className="text-xs text-red-600 hover:underline">
              {t("ingestion.clearList", "Clear List")}
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">{t("ingestion.fileName", "File Name")}</th>
                  <th className="py-2.5 px-3">{t("ingestion.source", "Source")}</th>
                  <th className="py-2.5 px-3">{t("ingestion.size", "Size")}</th>
                  <th className="py-2.5 px-3">{t("ingestion.detectedCrs", "Detected CRS")}</th>
                  <th className="py-2.5 px-3">{t("ingestion.status", "Status")}</th>
                  <th className="py-2.5 px-3 text-right">{t("common.actions", "Actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {uploadQueue.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-2.5 px-3 font-medium text-slate-900 flex items-center gap-2">
                      <span className="truncate max-w-[200px]">{item.name}</span>
                      {item.format && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-100 font-mono text-slate-600">
                          {item.format}
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3">{item.source}</td>
                    <td className="py-2.5 px-3">{item.size}</td>
                    <td className="py-2.5 px-3 font-mono text-[11px]">{item.crs}</td>
                    <td className="py-2.5 px-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                        item.status === "Completed" ? "bg-emerald-50 text-emerald-800 border border-emerald-200" :
                        item.status === "Failed" ? "bg-red-50 text-red-800 border border-red-200" :
                        "bg-blue-50 text-blue-800 border border-blue-200"
                      }`}>
                        {item.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {item.status === "Completed" && (
                        <button
                          onClick={() => handleOpenInspect(item)}
                          className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-semibold text-slate-700 bg-white border border-slate-200 rounded hover:bg-slate-50 shadow-2xs transition-colors"
                        >
                          <Eye size={12} />
                          {t("datasets.inspect", "Inspect")}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Categories */}
      <div className="space-y-3">
        <h2 className="text-sm font-bold text-slate-900">
          {t("ingestion.categoriesTitle", "Supported Ingestion Categories")}
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {dataSources.map((source) => {
            const Icon = source.icon;
            return (
              <div key={source.id} className="bg-white rounded-lg border border-slate-200 p-4 flex flex-col justify-between hover:border-slate-300">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="w-8 h-8 rounded bg-emerald-50 text-[#166534] flex items-center justify-center">
                      <Icon size={16} />
                    </div>
                    <span className="text-[10px] font-mono text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded">
                      {source.formats.split(",")[0]}
                    </span>
                  </div>
                  <h3 className="text-xs font-bold text-slate-900">{source.name}</h3>
                  <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2 min-h-[30px]">{source.description}</p>
                </div>
                <button
                  onClick={() => triggerSourceUpload(source)}
                  className="mt-3 w-full py-1.5 px-2 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 rounded text-xs font-medium flex items-center justify-center gap-1 transition-colors cursor-pointer"
                >
                  <Upload size={12} /> {t("ingestion.uploadBtn", "Upload")}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default DataIngestion;