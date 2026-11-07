import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ModernSelect, ModernSelectOption } from "./ModernSelect";
import { Home, Users } from "lucide-react";

describe("ModernSelect Component", () => {
  const options: ModernSelectOption[] = [
    {
      value: "home",
      label: "Home / Housing",
      sublabel: "Residence registration",
      icon: <Home data-testid="icon-home" className="w-4 h-4" />,
    },
    {
      value: "family",
      label: "Family / Children",
      sublabel: "Child benefits and custody",
      icon: <Users data-testid="icon-family" className="w-4 h-4" />,
      badge: <span data-testid="badge-family">Popular</span>,
    },
    {
      value: "archived",
      label: "Archived Items",
      disabled: true,
    },
  ];

  it("renders trigger with placeholder when no value is selected", () => {
    const handleChange = vi.fn();
    render(
      <ModernSelect
        id="test-select"
        value=""
        onChange={handleChange}
        options={options}
        placeholder="Choose category..."
      />
    );

    expect(screen.getByText("Choose category...")).toBeInTheDocument();
  });

  it("renders selected item label and icon in the trigger", () => {
    const handleChange = vi.fn();
    render(
      <ModernSelect
        id="test-select"
        value="home"
        onChange={handleChange}
        options={options}
      />
    );

    const trigger = screen.getByRole("button");
    expect(trigger).toHaveTextContent("Home / Housing");
    expect(screen.getByTestId("icon-home")).toBeInTheDocument();
  });

  it("opens popover on click, shows options, and selects an option", () => {
    const handleChange = vi.fn();
    render(
      <ModernSelect
        id="test-select"
        value=""
        onChange={handleChange}
        options={options}
        placeholder="Choose..."
      />
    );

    // Click trigger button
    const trigger = screen.getByRole("button");
    fireEvent.click(trigger);

    // Listbox should be visible
    const listbox = screen.getByRole("listbox");
    expect(listbox).toBeInTheDocument();
    expect(screen.getByText("Child benefits and custody")).toBeInTheDocument();
    expect(screen.getByTestId("badge-family")).toBeInTheDocument();

    // Click "Family / Children" option button
    const optionBtns = screen.getAllByRole("option");
    const familyOption = optionBtns.find((btn) => btn.textContent?.includes("Family / Children"));
    expect(familyOption).toBeDefined();
    fireEvent.click(familyOption!);

    expect(handleChange).toHaveBeenCalledWith("family");
  });

  it("filters options via search input when searchable is true", () => {
    const handleChange = vi.fn();
    render(
      <ModernSelect
        id="test-select"
        value=""
        onChange={handleChange}
        options={options}
        searchable
      />
    );

    // Open dropdown
    fireEvent.click(screen.getByRole("button"));

    const searchInput = screen.getByPlaceholderText("Search options...");
    expect(searchInput).toBeInTheDocument();

    // Type query matching only "Family"
    fireEvent.change(searchInput, { target: { value: "Child" } });

    const listbox = screen.getByRole("listbox");
    expect(listbox).not.toHaveTextContent("Home / Housing");
    expect(listbox).toHaveTextContent("Family / Children");
  });

  it("does not select disabled options", () => {
    const handleChange = vi.fn();
    render(
      <ModernSelect
        id="test-select"
        value=""
        onChange={handleChange}
        options={options}
      />
    );

    // Open dropdown
    fireEvent.click(screen.getByRole("button"));

    // Click disabled option
    const optionBtns = screen.getAllByRole("option");
    const disabledOption = optionBtns.find((btn) => btn.textContent?.includes("Archived Items"));
    expect(disabledOption).toBeDefined();
    fireEvent.click(disabledOption!);

    expect(handleChange).not.toHaveBeenCalled();
  });

  it("closes popover when pressing Escape", () => {
    render(
      <ModernSelect
        id="test-select"
        value=""
        onChange={vi.fn()}
        options={options}
      />
    );

    // Open dropdown
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("listbox")).toBeInTheDocument();

    // Press Escape
    fireEvent.keyDown(screen.getByRole("listbox"), { key: "Escape" });
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
});
