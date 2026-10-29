#!/usr/bin/env python3
"""Generate the complete synthetic Listing 1 projection; no CEN evidence transfers."""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
P = lambda value: {'type': 'Property', 'value': value}
R = lambda value: {'type': 'Relationship', 'object': value}
def encode(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')
def save(name, obj):
    (ROOT/'data'/name).write_text(json.dumps(obj, indent=2, allow_nan=False)+'\n')

def main():
    policy = json.loads((ROOT/'data/synthetic_policy.json').read_text())
    case = json.loads((ROOT/'results/scenario_results.json').read_text())[0]
    assert case['name'] == 'healthy' and case['accepted']
    expected = .5*(58/60)+.3+.2
    assert math.isclose(case['score'], expected)
    context = json.loads((ROOT/'contexts/data-quality-context.jsonld').read_text())['@context']
    context = dict(context)
    for term in ['evaluatedAt', 'ageSeconds', 'calibrationValid', 'firmwareVersion', 'siteScope', 'sourceQualificationAssumption', 'securityAssumption', 'ruleReference']:
        context[term] = 'https://example.org/dq-profile#'+term
    observation_id = 'urn:ngsi-ld:AirQualityObserved:synthetic:S01:example'
    assessment_id = 'urn:ngsi-ld:DataQualityAssessment:synthetic:S01:example'
    device_id = 'urn:ngsi-ld:Device:synthetic:S01'
    inputs = {'synthetic': True, 'policy': policy, 'case': case,
              'window': '[2026-06-15T09:59:01Z,2026-06-15T10:00:01Z)',
              'evaluatedAt': '2026-06-15T10:00:07Z',
              'sourceQualification': 'Assumed synthetic fixture only; no linkage to D1-D3 certificates'}
    digest = hashlib.sha256(encode(inputs)).hexdigest()
    observation = {'id': observation_id, 'type': 'AirQualityObserved', '@context': context,
                   'synthetic': P(True),
                   'NO2': {'type':'Property', 'value':42.1, 'unitCode':'GQ',
                           'observedAt':'2026-06-15T10:00:00Z',
                           'qualityScore':P(case['score']),
                           'qualityLevel':P('synthetic-eligible'),
                           'hasQualityAssessment':R(assessment_id)},
                   'refDevice':R(device_id)}
    assessment = {'id': assessment_id, 'type':'DataQualityAssessment', '@context': context,
                  'synthetic':P(True), 'refEntity':R(observation_id), 'refProperty':P('NO2'),
                  'metricCode':P('synthetic_runtime_weighted_score'), 'metricValue':P(case['score']),
                  'unit':P('1'), 'thresholdMin':P(policy['minimum_aggregate']),
                  'policyVersion':P(policy['id']), 'result':P('pass'), 'decision':P('accept'),
                  'completeness':P(case['completeness']), 'freshness':P(case['freshness']),
                  'schemaScore':P(case['schema']), 'sampleCount':P(58), 'expectedCount':P(60),
                  'ageSeconds':P(7), 'windowStart':P('2026-06-15T09:59:01Z'),
                  'windowEnd':P('2026-06-15T10:00:01Z'), 'evaluatedAt':P('2026-06-15T10:00:07Z'),
                  'evaluator':P('Synthetic local policy fixture'),
                  'sourceApplicability':P('Assumed for synthetic S01 at site A with firmware v1 only'),
                  'evidenceHash':P('sha256:'+digest),
                  'evidenceHashScope':P('listing1_inputs.json serialized by encode in make_listing_example.py'),
                  'evidenceIntegrityStatus':P('synthetic-fixture-only; no original source report'),
                  'sourceRecord':R('urn:sha256:'+digest)}
    # Device is a minimal declared synthetic fixture, not a certified source profile.
    context['Device'] = 'https://example.org/dq-profile#SyntheticDevice'
    device = {'id':device_id, 'type':'Device', '@context':context, 'synthetic':P(True),
              'calibrationValid':P(True), 'firmwareVersion':P('v1'), 'siteScope':P('site-A'),
              'sourceQualificationAssumption':P('Eligibility is assumed solely for this synthetic policy demonstration'),
              'securityAssumption':P('Authorization Boolean only; no TLS, identity or policy infrastructure')}
    assert observation['NO2']['hasQualityAssessment']['object'] == assessment['id']
    assert assessment['refEntity']['object'] == observation['id']
    assert observation['refDevice']['object'] == device['id']
    save('listing1_inputs.json', inputs)
    save('listing1_observation.jsonld', observation)
    save('listing1_assessment.jsonld', assessment)
    save('listing1_device.jsonld', device)
    print('Generated complete synthetic Listing 1: score, targets and input digest checked.')

if __name__ == '__main__':
    main()
