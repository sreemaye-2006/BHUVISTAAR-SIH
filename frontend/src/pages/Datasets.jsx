import React, { useState, useEffect, useMemo } from "react";
import {
  Database,
  Search,
  Upload,
  Eye,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import { listProjectDatasets, inspectDataset } from "../api/datasets";
import IngestionPreviewModal from "../components/ingestion/IngestionPreviewModal";

function Datasets() {
  const { t } = useTranslation();
  const { selectedProjectId } = useAuth();
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSource, setSelectedSource] = useState("all");

  // Detailed inspect modal state
  const [inspectModalOpen, setInspectModalOpen] = useState(false);
  const [inspectMetadata, setInspectMetadata] = useState(null);
  const [inspectFileName, setInspectFileName] = useState("");
  const [inspectingId, setInspectingId] = useState(null);

  useEffect(() => {
    if (selectedProjectId) {
      loadDatasets(selectedProjectId);
    }
  }, [selectedProjectId]);

  const loadDatasets = async (projectId) => {
    setLoading(true);
    try {
      const data = await listProjectDatasets(projectId);
      setDatasets(data || []);
    } catch (err) {
      console.error("Failed to load datasets:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleInspect = async (d) => {
    setInspectingId(d.id);
    setInspectFileName(d.file_name || d.name);
    try {
      const metadata = await inspectDataset(d.id);
      setInspectMetadata(metadata);
      setInspectModalOpen(true);
    } catch (err) {
      // Fallback metadata if inspection endpoint had an issue
      setInspectMetadata({
        format: d.file_name ? d.file_name.split(".").pop().toUpperCase() : "Unknown",
        dataset_type: d.dataset_type || "Vector",
        crs: d.crs || "EPSG:4326",
        geometry_type: d.dataset_type === "raster" ? "Raster Grid" : "Vector",
        feature_count: d.feature_count || 0,
        columns: [],
        map_ready: true,
        ml_ready: true,
      });
      setInspectModalOpen(true);
    } finally {
      setInspectingId(null);
    }
  };

  const filteredDatasets = useMemo(() => {
    return datasets.filter((d) => {
      const nameMatch = (d.name || "").toLowerCase().includes(searchQuery.toLowerCase());
      const sourceMatch = (d.source || "").toLowerCase().includes(searchQuery.toLowerCase());
      const typeMatch = (d.dataset_type || "").toLowerCase().includes(searchQuery.toLowerCase());

      const matchesSource =
        selectedSource === "all" || (d.source || "").toLowerCase() === selectedSource.toLowerCase();

      return (nameMatch || sourceMatch || typeMatch) && matchesSource;
    });
  }, [datasets, searchQuery, selectedSource]);

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              {t("datasets.title", "Dataset Repository")}
            </h1>
            {loading && <Loader2 className="h-4 w-4 animate-spin text-emerald-600" />}
          </div>
          <p className="text-xs text-slate-500 font-normal mt-0.5">
            {t("datasets.subtitle", "Registered spatial, tabular, raster, and imagery land records.")}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => selectedProjectId && loadDatasets(selectedProjectId)}
            className="p-1.5 bg-white hover:bg-slate-50 border border-slate-200 rounded text-slate-600 transition-colors"
            title={t("datasets.refresh", "Refresh Datasets")}
          >
            <RefreshCw size={14} />
          </button>
          <Link
            to="/ingestion"
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-[#166534] hover:bg-emerald-900 text-white rounded-md text-xs font-semibold transition-colors self-start shadow-sm"
          >
            <Upload size={14} />
            {t("datasets.importDataset", "+ Import Dataset")}
          </Link>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="bg-white rounded-lg border border-slate-200 p-3.5 flex flex-col sm:flex-row items-center justify-between gap-3 shadow-2xs">
        <div className="relative flex-1 w-full">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t("datasets.searchPlaceholder", "Search by dataset name, source, or type...")}
            className="w-full bg-slate-50 border border-slate-200 rounded-md pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:bg-white transition-colors"
          />
        </div>

        <div className="flex items-center gap-2">
          <select
            value={selectedSource}
            onChange={(e) => setSelectedSource(e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1.5 text-xs text-slate-700 cursor-pointer"
          >
            <option value="all">{t("datasets.allSources", "All Sources")}</option>
            <option value="cadastral">Cadastral</option>
            <option value="drone">Drone Survey</option>
            <option value="municipal">Municipal GIS</option>
            <option value="revenue">Revenue Records</option>
            <option value="gnss">GNSS / CORS</option>
          </select>
        </div>
      </div>

      {/* Main Table View */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          {filteredDatasets.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-xs">
              {t("datasets.noDatasets", "No datasets found for this project.")}
              <div className="mt-2">
                <Link to="/ingestion" className="text-emerald-700 font-semibold hover:underline">
                  {t("datasets.uploadNow", "Upload a dataset now")}
                </Link>
              </div>
            </div>
          ) : (
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">{t("datasets.datasetId", "Dataset ID")}</th>
                  <th className="py-2.5 px-3">{t("datasets.name", "Name")}</th>
                  <th className="py-2.5 px-3">{t("datasets.type", "Type")}</th>
                  <th className="py-2.5 px-3">{t("ingestion.source", "Source")}</th>
                  <th className="py-2.5 px-3">{t("ingestion.fileName", "File Name")}</th>
                  <th className="py-2.5 px-3">{t("datasets.features", "Records")}</th>
                  <th className="py-2.5 px-3">{t("common.status", "Status")}</th>
                  <th className="py-2.5 px-3 text-right">{t("common.actions", "Actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredDatasets.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-2.5 px-3 font-mono font-semibold text-slate-900">DS-{d.id}</td>
                    <td className="py-2.5 px-3 font-medium text-slate-900">{d.name}</td>
                    <td className="py-2.5 px-3 font-mono text-[11px] uppercase">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700">
                        {d.dataset_type || "vector"}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-700">{d.source || "Uploaded File"}</td>
                    <td className="py-2.5 px-3 font-mono text-[10px] text-slate-500 truncate max-w-[150px]" title={d.file_name}>
                      {d.file_name || "N/A"}
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-slate-900">{d.feature_count || 0}</td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 bg-emerald-50 text-[#166534] border border-emerald-200 rounded text-[10px] font-semibold capitalize">
                        {d.status || "uploaded"}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={() => handleInspect(d)}
                        disabled={inspectingId === d.id}
                        className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-semibold text-slate-700 bg-white border border-slate-200 rounded hover:bg-slate-50 shadow-2xs transition-colors cursor-pointer disabled:opacity-50"
                        title={t("datasets.inspect", "Inspect")}
                      >
                        {inspectingId === d.id ? <Loader2 size={12} className="animate-spin text-emerald-600" /> : <Eye size={12} />}
                        {t("datasets.inspect", "Inspect")}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Dataset Inspection Modal */}
      <IngestionPreviewModal
        isOpen={inspectModalOpen}
        onClose={() => setInspectModalOpen(false)}
        metadata={inspectMetadata}
        fileName={inspectFileName}
      />
    </div>
  );
}

export default Datasets;
