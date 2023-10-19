// use num_traits::Zero;
use pyo3::prelude::*;

#[pyfunction]
fn compute_multiplier_item_cost(
    amount: usize,
    current_multiplier: usize,
    item_price: usize,
    item_gain: usize,
) -> (usize, usize) {
    let cost = ((current_multiplier..=amount + current_multiplier - 1)
        .map(|x| (x as f64).powf(1.3))
        .sum::<f64>()
        * (item_price as f64))
        .floor() as usize;

    let gain = item_gain * amount;

    (cost, gain)
}

#[pyfunction]
fn compute_max_multiplier_item_purchase_amount(
    available_inches: usize,
    current_multiplier: usize,
    item_price: usize,
    item_gain: usize,
) -> (usize, usize, usize) {
    let mut max_reached = false;
    let mut min_amount = 0usize;
    let mut max_amount = 10usize;
    let mut amount = max_amount;

    loop {
        let old_amount = amount;
        amount = min_amount + ((max_amount as f64 - min_amount as f64) / 2.0).floor() as usize;

        let (cost, gain) =
            compute_multiplier_item_cost(amount, current_multiplier, item_price, item_gain);

        if amount == old_amount {
            return (amount, cost, gain);
        }

        if cost > available_inches {
            max_amount = amount;
            max_reached = true;
        } else {
            min_amount = amount;

            if !max_reached {
                max_amount *= 2;
            }
        }
    }
}

#[pymodule]
fn rust_utils(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compute_multiplier_item_cost, m)?)?;
    m.add_function(wrap_pyfunction!(
        compute_max_multiplier_item_purchase_amount,
        m
    )?)?;
    Ok(())
}
