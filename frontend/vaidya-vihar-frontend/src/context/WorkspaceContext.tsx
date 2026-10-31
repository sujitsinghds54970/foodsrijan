import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

export interface CompanyOption {
  id: number;
  name: string;
  slug?: string;
  is_active?: boolean;
  company_id?: number | null;
}

export interface BrandOption {
  id: number;
  company_id?: number | null;
  name: string;
  slug?: string;
  is_active?: boolean;
}

interface WorkspaceContextValue {
  company: CompanyOption | null;
  brand: BrandOption | null;
  companyId: number | null;
  brandId: number | null;
  companies: CompanyOption[];
  brands: BrandOption[];
  setCompany: (company: CompanyOption | null) => void;
  setBrand: (brand: BrandOption | null) => void;
  setCurrentWorkspace: (companyId: number | null, brandId?: number | null) => void;
  requestHeaders: Record<string, string>;
}

const DEFAULT_COMPANIES: CompanyOption[] = [
  { id: 1, name: 'FoodSrijan Group', slug: 'foodsrijan-group', is_active: true },
  { id: 2, name: 'Rasoi Republic', slug: 'rasoi-republic', is_active: true },
];

const DEFAULT_BRANDS: BrandOption[] = [
  { id: 1, company_id: 1, name: 'Rasoi Republic', slug: 'rasoi-republic', is_active: true },
  { id: 2, company_id: 2, name: 'Rasoi Republic', slug: 'rasoi-republic', is_active: true },
];

const WorkspaceContext = createContext<WorkspaceContextValue | undefined>(undefined);

const readStorageJson = <T,>(key: string, fallback: T): T => {
  if (typeof window === 'undefined') return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
};

const readStorageNumber = (key: string, fallback: number): number => {
  if (typeof window === 'undefined') return fallback;
  const value = window.localStorage.getItem(key);
  if (value === null || value === '') return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const normalizeCompanyList = (items: any[] | null | undefined): CompanyOption[] => {
  if (!Array.isArray(items) || !items.length) return DEFAULT_COMPANIES;
  return items
    .map((item) => {
      const companyId = Number(item.company_id ?? item.id ?? item.companyId ?? 0);
      if (!companyId) return null;
      const name = String(item.name || item.company_name || `Company ${companyId}`);
      return {
        id: companyId,
        company_id: companyId,
        name,
        slug: item.slug || name.toLowerCase().replace(/\s+/g, '-'),
        is_active: item.is_active ?? true,
      };
    })
    .filter(Boolean) as CompanyOption[];
};

const hydrateWorkspaceFromUser = (storedUser: any) => {
  const rawCompanies = Array.isArray(storedUser?.companies) ? storedUser.companies : [];
  if (!rawCompanies.length) return null;
  return normalizeCompanyList(rawCompanies);
};

export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [companies, setCompanies] = useState<CompanyOption[]>(DEFAULT_COMPANIES);
  const [brands, setBrands] = useState<BrandOption[]>(DEFAULT_BRANDS);
  const [company, setCompanyState] = useState<CompanyOption | null>(DEFAULT_COMPANIES[0]);
  const [brand, setBrandState] = useState<BrandOption | null>(DEFAULT_BRANDS[0]);

  const syncFromStoredUser = useCallback(() => {
    try {
      const storedUser = readStorageJson<any | null>('user', null);
      const userCompanies = hydrateWorkspaceFromUser(storedUser);
      const storedCompanies = userCompanies || readStorageJson<CompanyOption[]>('workspace.companies', DEFAULT_COMPANIES);
      const storedBrands = readStorageJson<BrandOption[]>('workspace.brands', DEFAULT_BRANDS);

      const nextCompanies = storedCompanies.length ? storedCompanies : DEFAULT_COMPANIES;
      const nextBrands = storedBrands.length ? storedBrands : DEFAULT_BRANDS;

      setCompanies(nextCompanies);
      setBrands(nextBrands);

      const preferredCompanyId = Number(
        storedUser?.current_company_id ??
        storedUser?.company_id ??
        readStorageNumber('workspace.companyId', nextCompanies[0]?.id ?? DEFAULT_COMPANIES[0].id)
      );
      const preferredBrandId = Number(readStorageNumber('workspace.brandId', nextBrands[0]?.id ?? DEFAULT_BRANDS[0].id));

      const nextCompany = nextCompanies.find((item) => Number(item.id) === preferredCompanyId) ?? nextCompanies[0] ?? null;
      const nextBrand = nextBrands.find((item) => Number(item.id) === preferredBrandId)
        ?? nextBrands.find((item) => Number(item.company_id ?? 0) === Number(nextCompany?.id ?? 0))
        ?? nextBrands[0]
        ?? null;

      setCompanyState(nextCompany);
      setBrandState(nextBrand);
    } catch {
      const storedCompanies = readStorageJson<CompanyOption[]>('workspace.companies', DEFAULT_COMPANIES);
      const storedBrands = readStorageJson<BrandOption[]>('workspace.brands', DEFAULT_BRANDS);
      const nextCompanies = storedCompanies.length ? storedCompanies : DEFAULT_COMPANIES;
      const nextBrands = storedBrands.length ? storedBrands : DEFAULT_BRANDS;
      setCompanies(nextCompanies);
      setBrands(nextBrands);
      setCompanyState(nextCompanies[0] ?? null);
      setBrandState(nextBrands[0] ?? null);
    }
  }, []);

  useEffect(() => {
    syncFromStoredUser();
  }, [syncFromStoredUser]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const onUserUpdated = (event: Event) => {
      const detail = (event as CustomEvent).detail;
      const user = detail && typeof detail === 'object' ? detail : null;
      if (user?.companies?.length) {
        const nextCompanies = normalizeCompanyList(user.companies);
        const idToSelect = Number(user.current_company_id ?? user.company_id ?? nextCompanies[0].id);
        const selectedCompany = nextCompanies.find((item) => Number(item.id) === idToSelect) ?? nextCompanies[0];
        setCompanies(nextCompanies);
        setCompanyState(selectedCompany);
        if (selectedCompany) {
          window.localStorage.setItem('workspace.companyId', String(selectedCompany.id));
          window.localStorage.setItem('workspace.companies', JSON.stringify(nextCompanies));
        }
      } else {
        syncFromStoredUser();
      }
    };

    window.addEventListener('workspace:user-updated', onUserUpdated as EventListener);
    return () => window.removeEventListener('workspace:user-updated', onUserUpdated as EventListener);
  }, [syncFromStoredUser]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem('workspace.companies', JSON.stringify(companies));
  }, [companies]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem('workspace.brands', JSON.stringify(brands));
  }, [brands]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (company?.id) {
      window.localStorage.setItem('workspace.companyId', String(company.id));
    }
  }, [company]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (brand?.id) {
      window.localStorage.setItem('workspace.brandId', String(brand.id));
    }
  }, [brand]);

  const setCompany = useCallback((nextCompany: CompanyOption | null) => {
    setCompanyState(nextCompany);
    if (!nextCompany) return;
    setBrandState((currentBrand) => {
      if (!currentBrand || currentBrand.company_id === nextCompany.id || currentBrand.company_id == null) {
        return brands.find((item) => item.company_id === nextCompany.id) ?? currentBrand ?? brands[0] ?? null;
      }
      return currentBrand;
    });
  }, [brands]);

  const setBrand = useCallback((nextBrand: BrandOption | null) => {
    setBrandState(nextBrand);
  }, []);

  const setCurrentWorkspace = useCallback((companyId: number | null, brandId: number | null = null) => {
    const nextCompany = companies.find((item) => item.id === companyId) ?? companies[0] ?? null;
    const nextBrand = brands.find((item) => item.id === brandId)
      ?? brands.find((item) => item.company_id === nextCompany?.id)
      ?? brands[0]
      ?? null;

    setCompanyState(nextCompany);
    setBrandState(nextBrand);
  }, [brands, companies]);

  const companyId = company?.id ?? null;
  const brandId = brand?.id ?? null;

  const requestHeaders = useMemo<Record<string, string>>(() => ({
    'X-Company-ID': companyId ? String(companyId) : '',
    'X-Brand-ID': brandId ? String(brandId) : '',
  }), [brandId, companyId]);

  const value = useMemo<WorkspaceContextValue>(() => ({
    company,
    brand,
    companyId,
    brandId,
    companies,
    brands,
    setCompany,
    setBrand,
    setCurrentWorkspace,
    requestHeaders,
  }), [brand, brandId, brands, company, companyId, companies, requestHeaders, setBrand, setCompany, setCurrentWorkspace]);

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
};

export const useWorkspace = () => {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
};
