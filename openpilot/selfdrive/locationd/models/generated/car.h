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
void car_err_fun(double *nom_x, double *delta_x, double *out_4327917516872155276);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_4692565444185876394);
void car_H_mod_fun(double *state, double *out_7616727919548478084);
void car_f_fun(double *state, double dt, double *out_6487004241572605689);
void car_F_fun(double *state, double dt, double *out_8695749791635856087);
void car_h_25(double *state, double *unused, double *out_4925446229357577593);
void car_H_25(double *state, double *unused, double *out_7111393477348181372);
void car_h_24(double *state, double *unused, double *out_2345626481440441499);
void car_H_24(double *state, double *unused, double *out_3109681398717672739);
void car_h_30(double *state, double *unused, double *out_7873172219713062554);
void car_H_30(double *state, double *unused, double *out_194703135856564617);
void car_h_26(double *state, double *unused, double *out_8716104515021809936);
void car_H_26(double *state, double *unused, double *out_7593847277487314020);
void car_h_27(double *state, double *unused, double *out_5907530322692875705);
void car_H_27(double *state, double *unused, double *out_2369466447656989528);
void car_h_29(double *state, double *unused, double *out_8476488104389540071);
void car_H_29(double *state, double *unused, double *out_315528208457827567);
void car_h_28(double *state, double *unused, double *out_7537540483355830266);
void car_H_28(double *state, double *unused, double *out_4766870808611703007);
void car_h_31(double *state, double *unused, double *out_6750462618001623087);
void car_H_31(double *state, double *unused, double *out_7080747515471220944);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}