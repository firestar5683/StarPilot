#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_err_fun(double *nom_x, double *delta_x, double *out_716521331412150656);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_6589697627091751304);
void car_H_mod_fun(double *state, double *out_6769065913804312214);
void car_f_fun(double *state, double dt, double *out_8306240271467682519);
void car_F_fun(double *state, double dt, double *out_8746322931733637628);
void car_h_25(double *state, double *unused, double *out_7997028965739177928);
void car_H_25(double *state, double *unused, double *out_1865374088619647374);
void car_h_24(double *state, double *unused, double *out_1561922556630116050);
void car_H_24(double *state, double *unused, double *out_5553017545057279519);
void car_h_30(double *state, double *unused, double *out_3364047373528769227);
void car_H_30(double *state, double *unused, double *out_6393070418747255572);
void car_h_26(double *state, double *unused, double *out_8589954589364094174);
void car_H_26(double *state, double *unused, double *out_5606877407493703598);
void car_h_27(double *state, double *unused, double *out_2239044051745439972);
void car_H_27(double *state, double *unused, double *out_4169476347563312355);
void car_h_29(double *state, double *unused, double *out_5984715746865394519);
void car_H_29(double *state, double *unused, double *out_5882839074432863388);
void car_h_28(double *state, double *unused, double *out_418921978945908094);
void car_H_28(double *state, double *unused, double *out_7481505982207157654);
void car_h_31(double *state, double *unused, double *out_5000636040905266768);
void car_H_31(double *state, double *unused, double *out_6233085509727055074);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}