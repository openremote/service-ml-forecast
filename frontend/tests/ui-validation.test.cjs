const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const ts = require('typescript');

function sourceExports(relative) {
    const source = fs.readFileSync(path.join(__dirname, '..', 'src', relative), 'utf8');
    const { outputText } = ts.transpileModule(source, {
        compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
    });
    const exported = {};
    new Function('exports', outputText)(exported);
    return exported;
}

const { weaValidationMessage } = sourceExports('pages/model-configs/wea-validation.ts');
const { responseError } = sourceExports('services/api-errors.ts');
const base = { past_period: 'P7D', past_count: 4, forecast_frequency: '1h', forecast_periods: 24 };

for (const [name, settings] of [
    ['weekly default', {}],
    ['exact weekly horizon', { forecast_periods: 168 }],
    ['equivalent hours', { past_period: 'PT168H', forecast_periods: 168 }],
    ['equivalent weeks', { past_period: 'P1W', forecast_periods: 168 }],
    ['combined elapsed duration', { past_period: 'P6DT24H', forecast_periods: 168 }],
    ['half-hourly boundary', { forecast_frequency: '30min', forecast_periods: 336 }],
    ['two-hourly boundary', { forecast_frequency: '2h', forecast_periods: 84 }],
    ['one historical period', { past_count: 1 }],
    ['maximum historical periods', { past_count: 100 }],
    ['whole milliseconds', { past_period: 'PT1S', forecast_frequency: '250ms', forecast_periods: 4 }]
]) {
    test(`WEA accepts ${name}`, () => assert.equal(weaValidationMessage({ ...base, ...settings }), null));
}

for (const [name, settings, message] of [
    ['too long weekly horizon', { forecast_periods: 169 }, /forecast horizon/i],
    ['too long half-hourly horizon', { forecast_frequency: '30min', forecast_periods: 337 }, /forecast horizon/i],
    ['too long two-hourly horizon', { forecast_frequency: '2h', forecast_periods: 85 }, /forecast horizon/i],
    ['zero count', { past_count: 0 }, /between 1 and 100/],
    ['excess count', { past_count: 101 }, /between 1 and 100/],
    ['fractional count', { past_count: 1.5 }, /whole number/],
    ['calendar month', { past_period: 'P1M' }, /Months and years/],
    ['calendar year', { past_period: 'P1Y' }, /Months and years/],
    ['zero past period', { past_period: 'P0D' }, /positive fixed/],
    ['empty past period', { past_period: '' }, /positive fixed/],
    ['zero frequency', { forecast_frequency: '0h' }, /Time between/],
    ['negative frequency', { forecast_frequency: '-1h' }, /Time between/],
    ['zero horizon', { forecast_periods: 0 }, /positive whole/],
    ['fractional horizon', { forecast_periods: 1.5 }, /positive whole/],
    ['nonfinite horizon', { forecast_periods: Infinity }, /positive whole/]
]) {
    test(`WEA explains ${name}`, () => assert.match(weaValidationMessage({ ...base, ...settings }), message));
}

test('API shows the backend model validation reason without echoing submitted inputs', async () => {
    const response = new Response(
        JSON.stringify({
            detail: [{ msg: 'Value error, WEA forecast horizon must not exceed the past period', input: { private: 'do not display' } }]
        }),
        { status: 422 }
    );
    assert.equal(
        (await responseError(response, 'Could not save')).message,
        'Weighted Exponential Average forecast horizon must not exceed the past period'
    );
});
test('API combines and deduplicates multiple validation messages', async () => {
    const response = new Response(JSON.stringify({ detail: [{ msg: 'Bad lags' }, { msg: 'Bad lags' }, { msg: 'Bad horizon' }] }), {
        status: 422
    });
    assert.equal((await responseError(response, 'Could not save')).message, 'Bad lags Bad horizon');
});
test('API preserves a useful string reason', async () => {
    assert.equal(
        (
            await responseError(
                new Response(JSON.stringify({ detail: 'Target already has an enabled configuration' }), { status: 400 }),
                'Could not save'
            )
        ).message,
        'Target already has an enabled configuration'
    );
});
test('API identifies the user-facing field for a numeric bound error', async () => {
    const response = new Response(
        JSON.stringify({ detail: [{ loc: ['body', 'xgboost', 'forecast_periods'], msg: 'Input should be greater than or equal to 1' }] }),
        { status: 422 }
    );
    assert.equal(
        (await responseError(response, 'Could not save')).message,
        'Forecasted datapoints: Input should be greater than or equal to 1'
    );
});
for (const [name, body] of [
    ['HTML proxy response', '<html>Error</html>'],
    ['empty response', ''],
    ['unexpected JSON', '{}'],
    ['malformed detail', '{"detail":[null,42,{}]}']
]) {
    test(`API has a useful fallback for ${name}`, async () => {
        assert.equal((await responseError(new Response(body, { status: 502 }), 'Could not save')).message, 'Could not save (502)');
    });
}
