"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { Organization, UIThemeConfig } from "../types";
import { getCurrentOrganization } from "../services/portalClient";
import { useAuth } from "@/features/auth/context/AuthProvider";
import {
  applyBrandThemeToDocument,
  clearDocumentRootBrandVariables,
  clearPersistedBrandTheme,
  readPersistedBrandTheme,
} from "../utils/theme";

interface OrganizationContextType {
  organization: Organization | null;
  loading: boolean;
  refreshOrganization: () => Promise<void>;
  effectiveThemeConfig: UIThemeConfig | null;
  setPreviewThemeConfig: (config: UIThemeConfig | null) => void;
}

const OrganizationContext = createContext<OrganizationContextType>({
  organization: null,
  loading: true,
  refreshOrganization: async () => {},
  effectiveThemeConfig: null,
  setPreviewThemeConfig: () => {},
});

export function OrganizationProvider({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [cachedThemeConfig, setCachedThemeConfig] = useState<UIThemeConfig | null>(null);
  const [previewThemeConfig, setPreviewThemeConfig] = useState<UIThemeConfig | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    clearDocumentRootBrandVariables();
    setCachedThemeConfig(readPersistedBrandTheme());
  }, []);

  const fetchOrg = useCallback(async () => {
    if (!user) {
      setOrganization(null);
      setCachedThemeConfig(null);
      setPreviewThemeConfig(null);
      clearPersistedBrandTheme();
      setLoading(false);
      return;
    }
    try {
      const data = await getCurrentOrganization();
      setOrganization(data);
      setCachedThemeConfig(data?.ui_theme_config ?? null);
      applyBrandThemeToDocument(data?.ui_theme_config, { persist: true });
    } catch {
      setOrganization(null);
      setCachedThemeConfig(null);
      setPreviewThemeConfig(null);
      clearPersistedBrandTheme();
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (!authLoading) {
      fetchOrg();
    }
  }, [authLoading, fetchOrg]);

  const effectiveThemeConfig =
    previewThemeConfig ?? organization?.ui_theme_config ?? cachedThemeConfig;

  return (
    <OrganizationContext.Provider
      value={{
        organization,
        loading,
        refreshOrganization: fetchOrg,
        effectiveThemeConfig,
        setPreviewThemeConfig,
      }}
    >
      {children}
    </OrganizationContext.Provider>
  );
}

export function useOrganization() {
  return useContext(OrganizationContext);
}
