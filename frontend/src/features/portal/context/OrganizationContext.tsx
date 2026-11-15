"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { Organization } from "../types";
import { getCurrentOrganization } from "../services/portalClient";
import { useAuth } from "@/features/auth/context/AuthProvider";
import {
  applyBrandThemeToDocument,
  clearPersistedBrandTheme,
  hydratePersistedBrandTheme,
} from "../utils/theme";

interface OrganizationContextType {
  organization: Organization | null;
  loading: boolean;
  refreshOrganization: () => Promise<void>;
}

const OrganizationContext = createContext<OrganizationContextType>({
  organization: null,
  loading: true,
  refreshOrganization: async () => {},
});

export function OrganizationProvider({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    hydratePersistedBrandTheme();
  }, []);

  const fetchOrg = useCallback(async () => {
    if (!user) {
      setOrganization(null);
      clearPersistedBrandTheme();
      setLoading(false);
      return;
    }
    try {
      const data = await getCurrentOrganization();
      setOrganization(data);
      applyBrandThemeToDocument(data?.ui_theme_config, { persist: true });
    } catch {
      setOrganization(null);
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

  return (
    <OrganizationContext.Provider
      value={{
        organization,
        loading,
        refreshOrganization: fetchOrg,
      }}
    >
      {children}
    </OrganizationContext.Provider>
  );
}

export function useOrganization() {
  return useContext(OrganizationContext);
}
