import { test, expect } from '@playwright/test';

test.describe('End-to-End Flow', () => {
  test('upload -> cohort polling -> results -> collusion', async ({ page }) => {
    test.setTimeout(90000);
    // 0. Pre-authenticate via storage
    await page.addInitScript(() => {
      sessionStorage.setItem('token', 'mock_token');
      localStorage.setItem('token', 'mock_token');
    });

    // 1. Mock API Responses (explicitly targeting backend API port 8000)
    await page.route('http://localhost:8000/rubrics', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 'r1', title: 'Biology Basics', max_score: 10, criteria: [] }
        ])
      });
    });

    await page.route('http://localhost:8000/submissions/batch', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ cohort_id: 'c1', jobs: [{ job_id: 'j1', file_name: 'test1.pdf' }] })
      });
    });

    await page.route('http://localhost:8000/cohorts/c1', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'c1',
          name: 'Batch Upload',
          jobs: [{ job_id: 'j1', file_name: 'test1.pdf', status: 'DONE', doc_id: 'd1' }]
        })
      });
    });

    await page.route('http://localhost:8000/jobs/*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: 'j1',
          status: 'DONE',
          doc_id: 'd1',
          file_name: 'test1.pdf'
        })
      });
    });

    await page.route('http://localhost:8000/results/d1', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          doc_id: 'd1',
          rubric_id: 'r1',
          total: 8,
          max_total: 10,
          per_criterion: [
            { criterion_id: 'c1', marks: 2, credit: 1.0, label: 'FULL_CREDIT', trusted: true }
          ]
        })
      });
    });

    await page.route('http://localhost:8000/results/d1/pdf', async route => {
      // Mock an empty PDF blob
      await route.fulfill({
        status: 200,
        contentType: 'application/pdf',
        body: Buffer.from('%PDF-1.4\n%EOF\n')
      });
    });

    await page.route('http://localhost:8000/cohorts/c1/collusion', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          cohort_id: 'c1',
          doc_pairs: [
            { a: 'd1', b: 'd2', similarity: 0.95, matching_props: ['test::test'] }
          ]
        })
      });
    });

    // 2. Start at Dashboard
    await page.goto('http://localhost:3000');
    await expect(page.locator('text=Biology Basics')).toBeVisible();

    // 3. Navigate to Upload
    await page.click('nav a:has-text("Upload")');
    await expect(page.getByRole('heading', { name: 'Upload Submissions' })).toBeVisible();

    // 4. Submit Batch with 2 files
    const file1 = { name: 'test1.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4 sample 1') };
    const file2 = { name: 'test2.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4 sample 2') };
    await page.setInputFiles('input[type="file"]', [file1, file2]);
    await expect(page.locator('select option[value="r1"]')).toBeAttached();
    await page.selectOption('select', 'r1');
    await page.click('button:has-text("Upload and Grade")');

    // 5. Check Cohort page
    await expect(page.getByRole('heading', { name: 'Cohort: Batch Upload' })).toBeVisible();
    await expect(page.locator('text=test1.pdf')).toBeVisible();
    await expect(page.locator('text=DONE').first()).toBeVisible();
    
    // Save screenshot of cohort
    await page.screenshot({ path: '../docs/screenshots/cohort.png' });

    // 6. Navigate to Results
    await page.locator('text=View Result').first().click();
    await expect(page.getByRole('heading', { name: 'Result for d1' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Annotated PDF' })).toBeVisible();
    
    // Save screenshot of result
    await page.screenshot({ path: '../docs/screenshots/result.png', fullPage: true });

    // 7. Go back to Cohort and check Collusion
    await page.goto('http://localhost:3000/cohorts/c1');
    await page.click('text=View Collusion Report');
    await expect(page.getByRole('heading', { name: 'Collusion Report for Cohort c1' })).toBeVisible();
    await expect(page.locator('text=Pair Similarity: 95.0%')).toBeVisible();
    
    // Save screenshot of collusion
    await page.screenshot({ path: '../docs/screenshots/collusion.png' });
  });
});
