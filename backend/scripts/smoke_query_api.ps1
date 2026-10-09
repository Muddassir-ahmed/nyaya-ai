param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"


function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw "ASSERTION FAILED: $Message"
    }
}


function Invoke-NyayaQuery {
    param(
        [string]$Query
    )

    $body = @{
        query = $Query
    } | ConvertTo-Json

    return Invoke-RestMethod `
        -Method POST `
        -Uri "$BaseUrl/query" `
        -ContentType "application/json" `
        -Body $body
}


$tests = @(
    @{
        Name = "Exact Article 21"
        Query = "What does Article 21 say?"
        Domain = "constitutional"
        MinEvidence = 1
        SummaryContains = $null
        ReasonContains = $null
        ExpectValidation = $true
    },
    @{
        Name = "Exact Article 243-I"
        Query = "Explain Article 243-I"
        Domain = "constitutional"
        MinEvidence = 1
        SummaryContains = $null
        ReasonContains = $null
        ExpectValidation = $true
    },
    @{
        Name = "Omitted Article 238"
        Query = "What does Article 238 say?"
        Domain = "constitutional"
        MinEvidence = 0
        MaxEvidence = 0
        SummaryContains = "omitted"
        ReasonContains = "omitted"
        ExpectValidation = $false
    },
    @{
        Name = "Nonexistent Article 999"
        Query = "What does Article 999 say?"
        Domain = "constitutional"
        MinEvidence = 0
        MaxEvidence = 0
        SummaryContains = "not found"
        ReasonContains = "not found"
        ExpectValidation = $false
    },
    @{
        Name = "Preamble"
        Query = "What does the Preamble say about secularism?"
        Domain = "constitutional"
        MinEvidence = 1
        SummaryContains = $null
        ReasonContains = $null
        ExpectValidation = $true
    },
    @{
        Name = "Seventh Schedule"
        Query = "What is in the Seventh Schedule?"
        Domain = "constitutional"
        MinEvidence = 1
        SummaryContains = $null
        ReasonContains = $null
        ExpectValidation = $true
    },
    @{
        Name = "Freedom of Speech"
        Query = "Explain freedom of speech in the Constitution"
        Domain = "constitutional"
        MinEvidence = 1
        SummaryContains = $null
        ReasonContains = $null
        ExpectValidation = $true
    },
    @{
        Name = "BNS Regression"
        Query = "What is the punishment for theft?"
        Domain = "criminal"
        MinEvidence = 1
        SummaryContains = $null
        ReasonContains = $null
        ExpectValidation = $true
    }
)


Write-Host ""
Write-Host "========================================"
Write-Host "NyayaAI /query E2E smoke test"
Write-Host "========================================"


$passed = 0


foreach ($test in $tests) {

    Write-Host ""
    Write-Host "----------------------------------------"
    Write-Host $test.Name
    Write-Host "----------------------------------------"

    Write-Host "Query:"
    Write-Host $test.Query

    $response = Invoke-NyayaQuery `
        -Query $test.Query

    $evidenceCount = @(
        $response.evidence
    ).Count

    Write-Host ""
    Write-Host "Route:               $($response.route)"
    Write-Host "Intent:              $($response.analysis.intent)"
    Write-Host "Domain:              $($response.analysis.domain)"
    Write-Host "Retrieval performed: $($response.retrieval_performed)"
    Write-Host "Evidence count:      $evidenceCount"
    Write-Host "Answer blocked:      $($response.answer_blocked)"

    if ($null -ne $response.routing_reason) {
        Write-Host "Routing reason:      $($response.routing_reason)"
    }

    if ($null -ne $response.legal_answer) {
        Write-Host ""
        Write-Host "Summary:"
        Write-Host $response.legal_answer.summary
    }

    if ($null -ne $response.validation) {
        Write-Host ""
        Write-Host "Citation valid:      $($response.validation.citation_valid)"
        Write-Host "Claim grounding:     $($response.validation.claim_grounding_valid)"
        Write-Host "Completeness:        $($response.validation.citation_completeness)"
    }

    # ------------------------------------
    # Core route assertions
    # ------------------------------------

    Assert-True `
        ($response.route -eq "legal") `
        "$($test.Name): expected legal route."

    Assert-True `
        ($response.analysis.domain -eq $test.Domain) `
        "$($test.Name): expected domain '$($test.Domain)', got '$($response.analysis.domain)'."

    Assert-True `
        ($response.retrieval_performed -eq $true) `
        "$($test.Name): retrieval_performed should be true."

    Assert-True `
        ($response.answer_blocked -eq $false) `
        "$($test.Name): answer was blocked by safety validation."

    Assert-True `
        ($null -ne $response.legal_answer) `
        "$($test.Name): legal_answer is missing."

    # ------------------------------------
    # Evidence assertions
    # ------------------------------------

    Assert-True `
        ($evidenceCount -ge $test.MinEvidence) `
        "$($test.Name): expected at least $($test.MinEvidence) evidence items, got $evidenceCount."

    if ($test.ContainsKey("MaxEvidence")) {
        Assert-True `
            ($evidenceCount -le $test.MaxEvidence) `
            "$($test.Name): expected at most $($test.MaxEvidence) evidence items, got $evidenceCount."
    }

    # ------------------------------------
    # Deterministic-answer assertions
    # ------------------------------------

    if ($null -ne $test.SummaryContains) {

        $summary = [string]$response.legal_answer.summary

        Assert-True `
            ($summary.ToLower().Contains(
                $test.SummaryContains.ToLower()
            )) `
            "$($test.Name): summary does not contain '$($test.SummaryContains)'."
    }

    if ($null -ne $test.ReasonContains) {

        $reason = [string]$response.routing_reason

        Assert-True `
            ($reason.ToLower().Contains(
                $test.ReasonContains.ToLower()
            )) `
            "$($test.Name): routing reason does not contain '$($test.ReasonContains)'."
    }

    # ------------------------------------
    # Validation behavior
    # ------------------------------------

    if ($test.ExpectValidation) {

        Assert-True `
            ($null -ne $response.validation) `
            "$($test.Name): expected citation/claim validation."
    }
    else {

        Assert-True `
            ($null -eq $response.validation) `
            "$($test.Name): deterministic response unexpectedly entered generated-answer validation."
    }

    Write-Host ""
    Write-Host "PASS ✅"

    $passed++
}


Write-Host ""
Write-Host "========================================"
Write-Host "E2E RESULTS"
Write-Host "========================================"

Write-Host "Passed: $passed / $($tests.Count)"


if ($passed -ne $tests.Count) {
    throw "E2E smoke test did not fully pass."
}


Write-Host ""
Write-Host "ALL /query E2E TESTS PASSED ✅"