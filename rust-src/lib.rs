// use num_traits::Zero;
use pyo3::prelude::*;

#[pyfunction]
fn compute_multiplier_item_cost(
    amount: usize,
    current_multiplier: usize,
    item_cost: usize,
    item_gain: usize,
) -> (usize, usize) {
    let cost = ((current_multiplier..=amount + current_multiplier - 1)
        .map(|x| (x as f64).powf(1.3))
        .sum::<f64>()
        * (item_cost as f64))
        .floor() as usize;

    let gain = item_gain * amount;

    (cost, gain)
}

#[pymodule]
fn rust_utils(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compute_multiplier_item_cost, m)?)
        .unwrap();
    Ok(())
}
