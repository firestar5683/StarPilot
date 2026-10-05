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
void car_err_fun(double *nom_x, double *delta_x, double *out_191040875433637227);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_449478399145670770);
void car_H_mod_fun(double *state, double *out_2217112053847292599);
void car_f_fun(double *state, double dt, double *out_5425352922863285243);
void car_F_fun(double *state, double dt, double *out_5183523293737892740);
void car_h_25(double *state, double *unused, double *out_1323322140775861569);
void car_H_25(double *state, double *unused, double *out_2722446496047589311);
void car_h_24(double *state, double *unused, double *out_9087948729282653086);
void car_H_24(double *state, double *unused, double *out_3567443104831284710);
void car_h_30(double *state, double *unused, double *out_1374282254885888156);
void car_H_30(double *state, double *unused, double *out_8807607236170345550);
void car_h_26(double *state, double *unused, double *out_2542026055962029893);
void car_H_26(double *state, double *unused, double *out_1019056822826466913);
void car_h_27(double *state, double *unused, double *out_1281083180032836082);
void car_H_27(double *state, double *unused, double *out_7464373525738781155);
void car_h_29(double *state, double *unused, double *out_1438269848383965227);
void car_H_29(double *state, double *unused, double *out_8297375891855953366);
void car_h_28(double *state, double *unused, double *out_677767295356358565);
void car_H_28(double *state, double *unused, double *out_668611781799699548);
void car_h_31(double *state, double *unused, double *out_2538361335652640083);
void car_H_31(double *state, double *unused, double *out_2753092457924549739);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}