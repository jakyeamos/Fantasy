import { useEffect, useState } from "react"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import type { LeagueTaxiConfig } from "@/api/types"
import { saveTaxiConfig, taxiConfigOptions } from "@/api/queries"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"

type TaxiConfigFormProps = {
  leagueId: string
}

export function TaxiConfigForm({ leagueId }: TaxiConfigFormProps) {
  const queryClient = useQueryClient()
  const q = useQuery(taxiConfigOptions(leagueId))
  const cfg = q.data?.config ?? null
  const [editing, setEditing] = useState(false)
  const [taxiSlots, setTaxiSlots] = useState(0)
  const [taxiYearsEligible, setTaxiYearsEligible] = useState(2)
  const [yearsProCutoff, setYearsProCutoff] = useState(2)
  const [manualExceptions, setManualExceptions] = useState("")

  useEffect(() => {
    if (editing) return
    if (cfg) {
      setTaxiSlots(cfg.taxi_slots)
      setTaxiYearsEligible(cfg.taxi_years_eligible)
      setYearsProCutoff(cfg.years_pro_cutoff)
      setManualExceptions((cfg.manual_exceptions ?? []).join(", "))
      return
    }
    setManualExceptions("")
  }, [editing, cfg])

  const saveMutation = useMutation({
    mutationFn: (next: LeagueTaxiConfig) => saveTaxiConfig(leagueId, next),
    onSuccess: async (data) => {
      queryClient.setQueryData(["leagues", leagueId, "taxi-config"], data)
      await queryClient.invalidateQueries({
        queryKey: ["intelligence", "lineup", leagueId],
      })
      await queryClient.invalidateQueries({
        queryKey: ["intelligence", "hygiene", leagueId],
      })
      await queryClient.invalidateQueries({
        queryKey: ["leagues", leagueId, "slot-occupancy"],
      })
      setEditing(false)
    },
  })

  if (q.isLoading && cfg === null) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Taxi configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-24 w-full" />
        </CardContent>
      </Card>
    )
  }

  if (q.isError) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">
            Failed to load taxi configuration.
          </p>
        </CardContent>
      </Card>
    )
  }

  const showSummary = cfg !== null && !editing

  if (showSummary) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle>Taxi configuration</CardTitle>
            <p className="mt-2 text-sm text-muted-foreground">
              Taxi slots: {cfg.taxi_slots} · Years eligible:{" "}
              {cfg.taxi_years_eligible} · Years pro cutoff:{" "}
              {cfg.years_pro_cutoff}
              {cfg.manual_exceptions.length > 0
                ? ` · Exceptions: ${cfg.manual_exceptions.length} player(s)`
                : ""}
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            type="button"
            onClick={() => setEditing(true)}
          >
            Edit Config
          </Button>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Taxi configuration</CardTitle>
        <p className="mt-2 text-sm text-muted-foreground">
          Pick values and hygiene suggestions stay approximate until this
          league&apos;s taxi configuration is saved.
        </p>
      </CardHeader>
      <CardContent>
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault()
            saveMutation.mutate({
              taxi_slots: taxiSlots,
              taxi_years_eligible: taxiYearsEligible,
              years_pro_cutoff: yearsProCutoff,
              manual_exceptions: manualExceptions
                .split(",")
                .map((value) => value.trim())
                .filter((value) => value.length > 0),
            })
          }}
        >
          <div className="space-y-2">
            <Label htmlFor="taxi-slots">Taxi Slots</Label>
            <input
              id="taxi-slots"
              type="number"
              min={0}
              max={10}
              className="h-11 w-full max-w-xs rounded-lg border border-border bg-card px-3 text-sm"
              value={taxiSlots}
              onChange={(ev) => setTaxiSlots(Number(ev.target.value))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="taxi-years">
              How many years a player can remain on taxi
            </Label>
            <input
              id="taxi-years"
              type="number"
              min={1}
              max={5}
              className="h-11 w-full max-w-xs rounded-lg border border-border bg-card px-3 text-sm"
              value={taxiYearsEligible}
              onChange={(ev) => setTaxiYearsEligible(Number(ev.target.value))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="years-pro">
              Max NFL experience to qualify for taxi
            </Label>
            <input
              id="years-pro"
              type="number"
              min={1}
              max={5}
              className="h-11 w-full max-w-xs rounded-lg border border-border bg-card px-3 text-sm"
              value={yearsProCutoff}
              onChange={(ev) => setYearsProCutoff(Number(ev.target.value))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="manual-exceptions">
              Manual exceptions (player IDs, comma-separated)
            </Label>
            <input
              id="manual-exceptions"
              type="text"
              className="h-11 w-full max-w-xs rounded-lg border border-border bg-card px-3 text-sm"
              value={manualExceptions}
              onChange={(ev) => setManualExceptions(ev.target.value)}
              placeholder="e.g. 4046, 7564"
            />
            <p className="text-xs text-muted-foreground">
              Player IDs your league allows on taxi outside normal eligibility
              rules.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={saveMutation.isPending}>
              Save Taxi Config
            </Button>
            {cfg ? (
              <Button
                type="button"
                variant="outline"
                onClick={() => setEditing(false)}
              >
                Cancel
              </Button>
            ) : null}
          </div>
          {saveMutation.isError ? (
            <p className="text-sm text-destructive">
              Failed to save the taxi configuration.
            </p>
          ) : null}
        </form>
      </CardContent>
    </Card>
  )
}
