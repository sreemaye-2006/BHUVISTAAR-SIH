import { useTranslation } from "react-i18next";
import Sidebar from "./Sidebar";
import Header from "./Header";

function Layout({ children }) {
  const { i18n } = useTranslation();
  const isRTL = i18n.language === "ur";

  return (
    <div
      className="min-h-screen bg-slate-50 flex text-slate-900 antialiased"
      dir={isRTL ? "rtl" : "ltr"}
    >
      <Sidebar />
      <div className={`flex-1 ${isRTL ? "mr-60" : "ml-60"} min-h-screen flex flex-col`}>
        <Header />
        <main className="flex-1 p-6 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

export default Layout;