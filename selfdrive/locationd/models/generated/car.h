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
void car_err_fun(double *nom_x, double *delta_x, double *out_6543135761510689107);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_2331655545426529005);
void car_H_mod_fun(double *state, double *out_6389313126975023722);
void car_f_fun(double *state, double dt, double *out_4897785971793930733);
void car_F_fun(double *state, double dt, double *out_1120359963151235251);
void car_h_25(double *state, double *unused, double *out_2169501381777287353);
void car_H_25(double *state, double *unused, double *out_1485621301790358882);
void car_h_24(double *state, double *unused, double *out_8386299954951130399);
void car_H_24(double *state, double *unused, double *out_1956078783833697606);
void car_h_30(double *state, double *unused, double *out_2444695444061793242);
void car_H_30(double *state, double *unused, double *out_6013317631917967080);
void car_h_26(double *state, double *unused, double *out_2413046201872073325);
void car_H_26(double *state, double *unused, double *out_5227124620664415106);
void car_h_27(double *state, double *unused, double *out_6236155437866939300);
void car_H_27(double *state, double *unused, double *out_3789723560734023863);
void car_h_29(double *state, double *unused, double *out_1645117212887109885);
void car_H_29(double *state, double *unused, double *out_5503086287603574896);
void car_h_28(double *state, double *unused, double *out_5811547118428763170);
void car_H_28(double *state, double *unused, double *out_3539456016038248645);
void car_h_31(double *state, double *unused, double *out_2741168024264044953);
void car_H_31(double *state, double *unused, double *out_1454975339913398454);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}