import LlmSettingsCard from "../components/LlmSettingsCard.jsx";
import EmbeddingSettingsCard from "../components/EmbeddingSettingsCard.jsx";
import AtlassianSettingsCard from "../components/AtlassianSettingsCard.jsx";
import FigmaSettingsCard from "../components/FigmaSettingsCard.jsx";
import SmtpSettingsCard from "../components/SmtpSettingsCard.jsx";
import S3SettingsCard from "../components/S3SettingsCard.jsx";
import DatabaseSettingsCard from "../components/DatabaseSettingsCard.jsx";
import SyncSettingsCard from "../components/SyncSettingsCard.jsx";

export default function ConfigurationPage() {
  return (
    <section id="view-config" className="view" hidden>
      <div className="cfg-grid">
        <LlmSettingsCard />
        <EmbeddingSettingsCard />
        <AtlassianSettingsCard />
        <FigmaSettingsCard />
        <SmtpSettingsCard />
        <S3SettingsCard />
        <DatabaseSettingsCard />
        <SyncSettingsCard />
      </div>
    </section>
  );
}
